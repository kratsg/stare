"""OAuth2 PKCE authentication flow for CERN Keycloak."""

from __future__ import annotations

import base64
import contextlib
import hashlib
import queue
import secrets
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlencode, urlparse

import filelock
import httpx
import jwt

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

from pydantic import ValidationError

from stare.exceptions import AuthenticationError, TokenExpiredError
from stare.models.auth import (
    JwtClaims,
    SessionInfo,
    TokenInfo,
    _OAuthTokenResponse,
    _StoredToken,
)
from stare.settings import StareSettings
from stare.storage import (
    _DEFAULT_TOKEN_PATH,
    FileTokenStorage,
    TokenStorage,
    get_default_storage,
)


def _create_s256_code_challenge(code_verifier: str) -> str:
    """Compute S256 code_challenge from code_verifier (RFC 7636 §4.2)."""
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _decode_jwt_payload(token: str) -> JwtClaims:
    """Decode a JWT payload section without verifying the signature.

    Returns an empty :class:`JwtClaims` on any parse failure so callers can
    always access fields safely.
    """
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        return JwtClaims.model_validate(payload)
    except (jwt.PyJWTError, ValidationError):
        pass
    return JwtClaims()


def _session_info(refresh_token: str | None) -> SessionInfo:
    """Describe a refresh token's session from its (unverified) claims.

    Opaque or missing refresh tokens decode to empty claims and are reported
    as online sessions with no known expiry.
    """
    claims = _decode_jwt_payload(refresh_token) if refresh_token else JwtClaims()
    return SessionInfo(offline=claims.typ == "Offline", refresh_expires_at=claims.exp)


class TokenManager:
    """Manages OAuth2 tokens: PKCE login flow, storage, and refresh."""

    def __init__(
        self,
        settings: StareSettings | None = None,
        token_path: Path | None = None,
        storage: TokenStorage | None = None,
    ) -> None:
        """Initialise the token manager with optional settings, path, and storage overrides."""
        self._settings = settings or StareSettings()
        self._token_path = token_path or _DEFAULT_TOKEN_PATH
        if storage is not None:
            self._storage: TokenStorage = storage
        elif token_path is not None:
            # Explicit path → always use file storage (no keyring lookup).
            self._storage = FileTokenStorage(token_path)
        else:
            # No explicit storage or path → honour STARE_TOKEN_STORAGE
            # ("auto" picks the keyring when available).
            self._storage = get_default_storage(backend=self._settings.token_storage)
        # In-memory cache for the RFC 8693 exchanged token (avoids a round-trip
        # to the token endpoint on every API call).
        self._exchanged_token: str | None = None
        self._exchanged_expires_at: int = 0
        # In-memory cache for the loaded PKCE base token (avoids a keyring/disk
        # round-trip on every API call while the token is still fresh).
        self._base_token: _StoredToken | None = None
        # Locking: thread lock guards in-process races; file lock guards
        # cross-process races (e.g. two CLI invocations refreshing at once).
        self._thread_lock = threading.Lock()
        self._storage.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._file_lock = filelock.FileLock(self._storage.lock_path)

    @property
    def token_path(self) -> Path:
        """Path to the stored token JSON file."""
        return self._token_path

    def login(
        self,
        *,
        on_url_ready: Callable[[str], None] | None = None,
        get_manual_code: Callable[[], str | None] | None = None,
        offline: bool = False,
    ) -> None:
        """Start PKCE browser flow; blocks until redirect received or manual code entered.

        Args:
            on_url_ready: Called with the authorization URL before the browser
                is opened — use this to display the URL to the user.
            get_manual_code: Called in a background thread to obtain a fallback
                authorization code (e.g. via user input) when the browser
                redirect cannot reach the local callback server.
            offline: Also request the ``offline_access`` scope so Keycloak
                issues an offline refresh token, which survives SSO logout
                and suits unattended jobs (cron, CI).
        """
        code_verifier = secrets.token_urlsafe(64)
        code_challenge = _create_s256_code_challenge(code_verifier)
        state = secrets.token_urlsafe(16)

        received: dict[str, str] = {}
        code_queue: queue.Queue[str] = queue.Queue(maxsize=1)
        stop_serving = threading.Event()

        class _CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # pylint: disable=invalid-name
                host = self.headers.get("Host", "")
                host_part = host.split(":")[0] if host else ""
                if host_part not in ("localhost", "127.0.0.1"):
                    self.send_response(403)
                    self.end_headers()
                    return
                parsed = urlparse(self.path)
                if parsed.path != "/callback":
                    self.send_response(404)
                    self.end_headers()
                    return
                params = parse_qs(parsed.query)
                if not params.get("state", [""])[0]:
                    self.send_response(400)
                    self.end_headers()
                    return
                received["code"] = params.get("code", [""])[0]
                received["state"] = params.get("state", [""])[0]
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"Authentication complete. You can close this window.")
                with contextlib.suppress(queue.Full):
                    code_queue.put_nowait(received["code"])
                stop_serving.set()

            def log_message(self, *args: object) -> None:  # suppress server logs
                pass

        try:
            server = HTTPServer(
                ("127.0.0.1", self._settings.callback_port), _CallbackHandler
            )
        except OSError as exc:
            msg = (
                f"Port {self._settings.callback_port} is already in use. "
                f"Set STARE_CALLBACK_PORT to a free port and register that "
                f"redirect URI with the Keycloak client, then run `stare auth login` again."
            )
            raise AuthenticationError(msg) from exc
        # Short per-request timeout so the serving loop can re-check its stop
        # condition between requests rather than blocking on a single one.
        server.timeout = 0.5
        redirect_uri = f"http://localhost:{self._settings.callback_port}/callback"

        auth_params = {
            "response_type": "code",
            "client_id": self._settings.client_id,
            "redirect_uri": redirect_uri,
            "scope": self._scopes(offline=offline),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        auth_url = f"{self._settings.auth_url}?{urlencode(auth_params)}"

        # Serve callback requests in a loop until a code is queued or the
        # deadline passes. Looping (rather than a single handle_request) keeps
        # login alive when a stray request — favicon probe, stale tab reload,
        # port scan — reaches the port before the real OAuth redirect.
        serving_deadline = time.monotonic() + 122.0

        def _serve() -> None:
            while not stop_serving.is_set() and time.monotonic() < serving_deadline:
                with contextlib.suppress(OSError):
                    server.handle_request()

        threading.Thread(target=_serve, daemon=True).start()

        # Notify caller so it can display the URL before opening the browser
        if on_url_ready is not None:
            on_url_ready(auth_url)

        webbrowser.open(auth_url)

        # Optionally accept a manual code in a parallel background thread
        if get_manual_code is not None:

            def _input_thread() -> None:
                code = get_manual_code()
                if code:
                    with contextlib.suppress(queue.Full):
                        code_queue.put_nowait(code)

            threading.Thread(target=_input_thread, daemon=True).start()

        # Block until the first code arrives (server callback or manual entry)
        try:
            code = code_queue.get(timeout=120)
        except queue.Empty as err:
            msg = (
                "Authentication timed out (120 seconds). Run `stare auth login` again."
            )
            raise AuthenticationError(msg) from err
        finally:
            # Stop the serving loop before closing so the thread doesn't spin
            # on the closed socket.
            stop_serving.set()
            server.server_close()

        # Validate state only when it was received from the server callback
        if received.get("state") and received["state"] != state:
            msg = "State mismatch in OAuth callback — possible CSRF attack."
            raise AuthenticationError(msg)

        if not code:
            msg = "No authorization code received."
            raise AuthenticationError(msg)

        try:
            with httpx.Client() as client:
                response = client.post(
                    self._settings.token_url,
                    data={
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": redirect_uri,
                        "client_id": self._settings.client_id,
                        "code_verifier": code_verifier,
                    },
                )
                response.raise_for_status()
                oauth_resp = _OAuthTokenResponse.model_validate(response.json())
        except (httpx.RequestError, httpx.HTTPStatusError) as exc:
            msg = f"Token request failed: {exc}"
            raise AuthenticationError(msg) from exc
        except ValidationError as exc:
            msg = f"Unexpected token response format: {exc}"
            raise AuthenticationError(msg) from exc

        if oauth_resp.id_token:
            self._validate_id_token(oauth_resp.id_token)

        token = _StoredToken.from_response(oauth_resp)
        self._storage.save(token)

    def _scopes(self, *, offline: bool) -> str:
        """Return the scopes to request, adding ``offline_access`` when asked."""
        scopes = self._settings.scopes.split()
        if offline and "offline_access" not in scopes:
            scopes.append("offline_access")
        return " ".join(scopes)

    def _validate_id_token(self, id_token: str) -> JwtClaims:
        """Validate and decode an ID token using the JWKS endpoint (PyJWT).

        Raises :exc:`~stare.exceptions.AuthenticationError` on any validation
        failure (expired, wrong issuer, wrong audience, bad signature, …).
        """
        try:
            jwks_client = jwt.PyJWKClient(self._settings.jwks_url)
            signing_key = jwks_client.get_signing_key_from_jwt(id_token)
            payload = jwt.decode(
                id_token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self._settings.client_id,
                issuer=self._settings.issuer,
            )
            return JwtClaims.model_validate(payload)
        except jwt.PyJWTError as exc:
            msg = f"ID token validation failed: {exc}"
            raise AuthenticationError(msg) from exc
        except ValidationError as exc:
            msg = f"ID token claims validation failed: {exc}"
            raise AuthenticationError(msg) from exc

    def logout(self) -> None:
        """Revoke tokens server-side (best-effort) then delete local storage."""
        with self._thread_lock, self._file_lock:
            token = self._storage.load()
            if token is not None:
                self._revoke_token(token.refresh_token, "refresh_token")
                self._revoke_token(token.access_token, "access_token")
            try:
                self._storage.delete()
            except Exception as exc:
                msg = f"Failed to remove stored credentials: {exc}"
                raise AuthenticationError(msg) from exc
            self._clear_cached_tokens()

    def _clear_cached_tokens(self) -> None:
        """Drop the in-memory base and exchanged tokens."""
        self._exchanged_token = None
        self._exchanged_expires_at = 0
        self._base_token = None

    def export_refresh_token(self, *, move: bool = False) -> str:
        """Return the stored offline refresh token for transfer to another host.

        Refuses online sessions, which would die with the SSO session. With
        ``move=True`` the local copy is deleted (without server-side
        revocation, so the exported token stays valid).

        Keycloak rotates refresh tokens, so once the other host refreshes, any
        copy kept here may be rejected on its next refresh.

        ``move=True`` is not transactional: the local copy is deleted before
        the caller delivers the returned token. If that delivery or the remote
        import fails, the session stays valid server-side but can no longer be
        revoked from this host (:meth:`logout` only revokes tokens still
        stored). A later ``login(offline=True)`` creates a separate session;
        it neither recovers nor revokes the orphaned one, which lapses only
        after the server's offline-session idle timeout.
        """
        with self._thread_lock, self._file_lock:
            token = self._storage.load()
            if token is None or not token.refresh_token:
                msg = "No stored session to export. Run `stare auth login --offline` first."
                raise AuthenticationError(msg)
            if not _session_info(token.refresh_token).offline:
                msg = (
                    "The stored session is not an offline session and would expire "
                    "with your SSO session. Run `stare auth login --offline` first."
                )
                raise AuthenticationError(msg)
            if move:
                self._storage.delete()
                self._clear_cached_tokens()
            return token.refresh_token

    def import_refresh_token(self, refresh_token: str) -> None:
        """Store a session from an offline refresh token exported elsewhere.

        The token is redeemed immediately, so a bad or expired token fails
        here rather than on the first unattended run. A rejected token leaves
        any session already stored on this host untouched.
        """
        refresh_token = refresh_token.strip()
        if not _session_info(refresh_token).offline:
            msg = (
                "Not an offline refresh token. Export one with `stare auth export` "
                "from a session created by `stare auth login --offline`."
            )
            raise AuthenticationError(msg)
        with self._thread_lock, self._file_lock:
            token = self._refresh(refresh_token, clear_on_reject=False)
            self._clear_cached_tokens()
            self._base_token = token

    def _revoke_token(self, token: str | None, token_type_hint: str) -> None:
        """POST token to the Keycloak revocation endpoint; never raises."""
        if not token:
            return
        with contextlib.suppress(Exception), httpx.Client() as client:
            client.post(
                self._settings.revocation_url,
                data={
                    "client_id": self._settings.client_id,
                    "token": token,
                    "token_type_hint": token_type_hint,
                },
            )

    def get_token(self) -> str:
        """Return a valid access token, refreshing and exchanging as needed.

        If ``settings.exchange_audience`` is set, the PKCE access token is
        exchanged for an audience-scoped token via RFC 8693.  The exchanged
        token is cached in memory to avoid a round-trip on every API call.
        """
        base_token = self._get_base_token()
        if not self._settings.exchange_audience:
            return base_token
        # Return cached exchange token if still valid (> buffer seconds left)
        if (
            self._exchanged_token
            and self._exchanged_expires_at
            > int(time.time()) + self._settings.exchange_token_buffer_seconds
        ):
            return self._exchanged_token
        return self._exchange_token(base_token)

    def _get_base_token(self) -> str:
        """Return the raw PKCE access token, refreshing via refresh_token if expired.

        A valid loaded token is cached in memory and returned without touching
        storage or the file lock. Storage is consulted only when the cache is
        absent or within the expiry margin (another process may have refreshed
        it meanwhile), refreshing via the refresh token as a last resort.
        """
        margin = self._settings.token_expiry_margin_seconds
        with self._thread_lock:
            cached = self._base_token
            if cached is not None and not cached.is_expired_with_margin(margin):
                return cached.access_token
            with self._file_lock:
                token = self._storage.load()
                if token is None:
                    msg = "Not authenticated. Run `stare auth login` first."
                    raise AuthenticationError(msg)

                if token.is_expired_with_margin(margin):
                    if not token.refresh_token:
                        msg = "Access token has expired and no refresh token is available. Run `stare auth login` again."
                        raise TokenExpiredError(msg)
                    token = self._refresh(token.refresh_token)

                self._base_token = token
                return token.access_token

    def _exchange_token(self, subject_token: str) -> str:
        """Exchange a PKCE access token for an audience-scoped token (RFC 8693).

        Raises :exc:`~stare.exceptions.TokenExpiredError` on HTTP failure.
        """
        try:
            with httpx.Client() as client:
                response = client.post(
                    self._settings.token_url,
                    data={
                        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
                        "client_id": self._settings.client_id,
                        "subject_token": subject_token,
                        "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
                        "audience": self._settings.exchange_audience,
                    },
                )
                response.raise_for_status()
                oauth_resp = _OAuthTokenResponse.model_validate(response.json())

        except httpx.HTTPStatusError as exc:
            msg = f"Token exchange failed ({exc.response.status_code}). Run `stare auth login` again."
            raise TokenExpiredError(msg) from exc
        except httpx.RequestError as exc:
            msg = f"Token exchange failed (network error): {exc}. Run `stare auth login` again."
            raise TokenExpiredError(msg) from exc
        except ValidationError as exc:
            msg = (
                f"Token exchange response invalid: {exc}. Run `stare auth login` again."
            )
            raise TokenExpiredError(msg) from exc
        self._exchanged_token = oauth_resp.access_token
        self._exchanged_expires_at = int(time.time()) + oauth_resp.expires_in
        return self._exchanged_token

    def _refresh(
        self, refresh_token: str, *, clear_on_reject: bool = True
    ) -> _StoredToken:
        """Exchange a refresh token for new tokens and persist them.

        With ``clear_on_reject`` (the default) a 4xx from Keycloak also deletes
        the stored tokens, since they were the ones rejected.
        """
        try:
            with httpx.Client() as client:
                response = client.post(
                    self._settings.token_url,
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                        "client_id": self._settings.client_id,
                    },
                )
                response.raise_for_status()
                oauth_resp = _OAuthTokenResponse.model_validate(response.json())
        except httpx.HTTPStatusError as exc:
            # Keycloak rotates refresh tokens — a 4xx means the stored token
            # is already invalidated server-side, so delete it locally too.
            if clear_on_reject:
                self._storage.delete()
                self._clear_cached_tokens()
            msg = f"Token refresh failed ({exc.response.status_code}). Run `stare auth login` again."
            raise TokenExpiredError(msg) from exc
        except httpx.RequestError as exc:
            msg = f"Token refresh failed (network error): {exc}. Run `stare auth login` again."
            raise TokenExpiredError(msg) from exc
        except ValidationError as exc:
            msg = (
                f"Token refresh response invalid: {exc}. Run `stare auth login` again."
            )
            raise TokenExpiredError(msg) from exc

        token = _StoredToken.from_response(oauth_resp)
        self._storage.save(token)
        return token

    def get_pkce_access_token(self) -> str:
        """Return the PKCE base access token (refreshing if needed).

        Never performs a token exchange regardless of ``exchange_audience``.
        Raises :exc:`~stare.exceptions.AuthenticationError` if not logged in.
        """
        return self._get_base_token()

    def get_pkce_id_token(self) -> str | None:
        """Return the stored PKCE id token, or None if absent or not logged in."""
        with contextlib.suppress(Exception):
            token = self._storage.load()
            if token is not None:
                return token.id_token
        return None

    def get_exchange_access_token(self) -> str | None:
        """Return the raw RFC 8693 exchanged access token.

        Returns None if ``exchange_audience`` is not configured.
        Performs the exchange if the cached token is absent or nearly expired.
        Raises :exc:`~stare.exceptions.AuthenticationError` if not logged in.
        """
        if not self._settings.exchange_audience:
            return None
        self.get_token()  # populates _exchanged_token
        return self._exchanged_token

    def is_authenticated(self) -> bool:
        """Return True if a non-expired token is stored."""
        with contextlib.suppress(Exception):
            token = self._storage.load()
            if token is not None:
                return not token.is_expired
        return False

    def get_token_info(self) -> TokenInfo | None:
        """Return token metadata and decoded JWT claims, or None if not stored.

        The JWT payload is decoded without signature verification — suitable
        only for display purposes, not security decisions.
        """
        with contextlib.suppress(Exception):
            token = self._storage.load()
            if token is not None:
                # Prefer id_token (contains identity claims); fall back to access_token.
                jwt_to_decode = token.id_token or token.access_token
                claims = _decode_jwt_payload(jwt_to_decode)
                return TokenInfo(
                    is_expired=token.is_expired,
                    expires_at=token.expires_at,
                    claims=claims,
                )
        return None

    def get_session_info(self) -> SessionInfo | None:
        """Return whether the stored session is offline, or None if not stored.

        Decoded from the refresh token without signature verification —
        suitable only for display purposes, not security decisions.
        """
        with contextlib.suppress(Exception):
            token = self._storage.load()
            if token is not None:
                return _session_info(token.refresh_token)
        return None

    def get_exchange_token_info(self) -> TokenInfo | None:
        """Decode and return info for the RFC 8693 exchanged token.

        Returns None if ``exchange_audience`` is not configured.
        Performs the exchange if the cached token is absent or nearly expired.
        Raises :exc:`~stare.exceptions.AuthenticationError` if not logged in.
        """
        if not self._settings.exchange_audience:
            return None
        # get_token() populates _exchanged_token / _exchanged_expires_at
        self.get_token()
        if self._exchanged_token is None:
            msg = (
                "get_token() completed but _exchanged_token was not set; this is a bug."
            )
            raise RuntimeError(msg)
        claims = _decode_jwt_payload(self._exchanged_token)
        return TokenInfo(
            is_expired=self._exchanged_expires_at < int(time.time()) + 60,
            expires_at=self._exchanged_expires_at,
            claims=claims,
        )

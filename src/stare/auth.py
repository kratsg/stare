"""OAuth2 PKCE authentication flow for CERN Keycloak."""

from __future__ import annotations

import base64
import binascii
import contextlib
import hashlib
import json
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
from stare.models.auth import JwtClaims, TokenInfo, _OAuthTokenResponse, _StoredToken
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
        payload_b64 = token.split(".")[1]
        # JWT uses base64url without padding; re-add it before decoding.
        payload_b64 += "=" * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        if isinstance(payload, dict):
            return JwtClaims.model_validate(payload)
    except (
        IndexError,
        ValueError,
        binascii.Error,
        json.JSONDecodeError,
        ValidationError,
    ):
        pass
    return JwtClaims()


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
            # No explicit storage or path → auto-detect (keyring if available).
            self._storage = get_default_storage()
        # In-memory cache for the RFC 8693 exchanged token (avoids a round-trip
        # to the token endpoint on every API call).
        self._exchanged_token: str | None = None
        self._exchanged_expires_at: int = 0
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
    ) -> None:
        """Start PKCE browser flow; blocks until redirect received or manual code entered.

        Args:
            on_url_ready: Called with the authorization URL before the browser
                is opened — use this to display the URL to the user.
            get_manual_code: Called in a background thread to obtain a fallback
                authorization code (e.g. via user input) when the browser
                redirect cannot reach the local callback server.
        """
        code_verifier = secrets.token_urlsafe(64)
        code_challenge = _create_s256_code_challenge(code_verifier)
        state = secrets.token_urlsafe(16)

        received: dict[str, str] = {}
        code_queue: queue.Queue[str] = queue.Queue(maxsize=1)

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
                received["code"] = params.get("code", [""])[0]
                received["state"] = params.get("state", [""])[0]
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"Authentication complete. You can close this window.")
                with contextlib.suppress(queue.Full):
                    code_queue.put_nowait(received["code"])

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
                f"redirect URI with the Keycloak client, then run `stare login` again."
            )
            raise AuthenticationError(msg) from exc
        server.timeout = 125.0  # slightly longer than the queue timeout below
        redirect_uri = f"http://localhost:{self._settings.callback_port}/callback"

        auth_params = {
            "response_type": "code",
            "client_id": self._settings.client_id,
            "redirect_uri": redirect_uri,
            "scope": self._settings.scopes,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        auth_url = f"{self._settings.auth_url}?{urlencode(auth_params)}"

        # Start callback server in a background thread
        def _serve() -> None:
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
            msg = "Authentication timed out (120 seconds). Run `stare login` again."
            raise AuthenticationError(msg) from err
        finally:
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
        token = self._storage.load()
        if token is not None:
            self._revoke_token(token.refresh_token, "refresh_token")
            self._revoke_token(token.access_token, "access_token")
        self._storage.delete()
        self._exchanged_token = None
        self._exchanged_expires_at = 0

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
        """Return the raw PKCE access token, refreshing via refresh_token if expired."""
        with self._thread_lock, self._file_lock:
            token = self._storage.load()
            if token is None:
                msg = "Not authenticated. Run `stare login` first."
                raise AuthenticationError(msg)

            if token.is_expired_with_margin(self._settings.token_expiry_margin_seconds):
                if not token.refresh_token:
                    msg = "Access token has expired and no refresh token is available. Run `stare login` again."
                    raise TokenExpiredError(msg)
                token = self._refresh(token.refresh_token)

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
            msg = f"Token exchange failed ({exc.response.status_code}). Run `stare login` again."
            raise TokenExpiredError(msg) from exc
        self._exchanged_token = oauth_resp.access_token
        self._exchanged_expires_at = int(time.time()) + oauth_resp.expires_in
        return self._exchanged_token

    def _refresh(self, refresh_token: str) -> _StoredToken:
        """Exchange a refresh token for new tokens and persist them."""
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
            self._storage.delete()
            self._exchanged_token = None
            self._exchanged_expires_at = 0
            msg = f"Token refresh failed ({exc.response.status_code}). Run `stare login` again."
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
        assert self._exchanged_token is not None
        claims = _decode_jwt_payload(self._exchanged_token)
        return TokenInfo(
            is_expired=self._exchanged_expires_at < int(time.time()) + 60,
            expires_at=self._exchanged_expires_at,
            claims=claims,
        )

"""OAuth2 PKCE authentication flow for CERN Keycloak."""

from __future__ import annotations

import base64
import contextlib
import json
import queue
import secrets
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
from authlib.oauth2.rfc7636 import create_s256_code_challenge
from platformdirs import user_data_dir
from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from collections.abc import Callable

from stare.exceptions import AuthenticationError, TokenExpiredError
from stare.settings import StareSettings

_DEFAULT_TOKEN_PATH = Path(user_data_dir("stare")) / "tokens.json"


class JwtClaims(BaseModel):
    """Decoded JWT payload claims from CERN Keycloak.

    ``extra="allow"`` preserves any claims not listed here so nothing is
    silently dropped when displaying or passing the object around.
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    sub: str | None = None
    preferred_username: str | None = None
    name: str | None = None
    email: str | None = None
    exp: int | None = None
    iat: int | None = None


class TokenInfo(BaseModel):
    """Token metadata and decoded JWT claims returned by :meth:`TokenManager.get_token_info`."""

    model_config = ConfigDict(populate_by_name=True)

    is_expired: bool
    expires_at: int
    claims: JwtClaims


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
    except (IndexError, ValueError):
        pass
    return JwtClaims()


class _OAuthTokenResponse(BaseModel):
    """Raw OAuth2 token endpoint response from CERN Keycloak."""

    access_token: str
    refresh_token: str | None = None
    token_type: str = "Bearer"
    expires_in: int = 3600
    id_token: str | None = None


class _StoredToken(BaseModel):
    """Token data persisted to disk after a successful login or refresh."""

    access_token: str
    refresh_token: str | None = None
    token_type: str = "Bearer"
    expires_at: int = 0
    id_token: str | None = None

    @classmethod
    def from_response(cls, resp: _OAuthTokenResponse) -> _StoredToken:
        """Build a stored token from an OAuth response, computing expires_at."""
        return cls(
            access_token=resp.access_token,
            refresh_token=resp.refresh_token,
            token_type=resp.token_type,
            expires_at=int(time.time()) + resp.expires_in,
            id_token=resp.id_token,
        )

    @property
    def is_expired(self) -> bool:
        """True if the token has expired or expires within 60 seconds."""
        return self.expires_at < int(time.time()) + 60


class TokenManager:
    """Manages OAuth2 tokens: PKCE login flow, storage, and refresh."""

    def __init__(
        self,
        settings: StareSettings | None = None,
        token_path: Path | None = None,
    ) -> None:
        self._settings = settings or StareSettings()
        self._token_path = token_path or _DEFAULT_TOKEN_PATH

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
        code_challenge = create_s256_code_challenge(code_verifier)
        state = secrets.token_urlsafe(16)

        received: dict[str, str] = {}
        code_queue: queue.Queue[str] = queue.Queue(maxsize=1)

        class _CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                parsed = urlparse(self.path)
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

        token = _StoredToken.from_response(oauth_resp)
        self._token_path.parent.mkdir(parents=True, exist_ok=True)
        self._token_path.write_text(token.model_dump_json())

    def logout(self) -> None:
        """Delete stored tokens."""
        if self._token_path.exists():
            self._token_path.unlink()

    def get_token(self) -> str:
        """Return a valid access token, refreshing if needed."""
        if not self._token_path.exists():
            msg = "Not authenticated. Run `stare login` first."
            raise AuthenticationError(msg)

        token = _StoredToken.model_validate_json(self._token_path.read_text())

        if token.is_expired:
            if not token.refresh_token:
                msg = "Access token has expired and no refresh token is available. Run `stare login` again."
                raise TokenExpiredError(msg)
            token = self._refresh(token.refresh_token)

        return token.access_token

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
            msg = f"Token refresh failed ({exc.response.status_code}). Run `stare login` again."
            raise TokenExpiredError(msg) from exc

        token = _StoredToken.from_response(oauth_resp)
        self._token_path.write_text(token.model_dump_json())
        return token

    def is_authenticated(self) -> bool:
        """Return True if a non-expired token is stored."""
        if not self._token_path.exists():
            return False
        with contextlib.suppress(Exception):
            token = _StoredToken.model_validate_json(self._token_path.read_text())
            return not token.is_expired
        return False

    def get_token_info(self) -> TokenInfo | None:
        """Return token metadata and decoded JWT claims, or None if not stored.

        The JWT payload is decoded without signature verification — suitable
        only for display purposes, not security decisions.
        """
        if not self._token_path.exists():
            return None
        with contextlib.suppress(Exception):
            token = _StoredToken.model_validate_json(self._token_path.read_text())
            # Prefer id_token (contains identity claims); fall back to access_token.
            jwt_to_decode = token.id_token or token.access_token
            claims = _decode_jwt_payload(jwt_to_decode)
            return TokenInfo(
                is_expired=token.is_expired,
                expires_at=token.expires_at,
                claims=claims,
            )
        return None

"""OAuth2 PKCE authentication flow for CERN Keycloak."""

from __future__ import annotations

import contextlib
import secrets
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
from authlib.oauth2.rfc7636 import create_s256_code_challenge
from platformdirs import user_data_dir
from pydantic import BaseModel

from stare.exceptions import AuthenticationError, TokenExpiredError
from stare.settings import StareSettings

_DEFAULT_TOKEN_PATH = Path(user_data_dir("stare")) / "tokens.json"


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

    def login(self) -> None:
        """Start PKCE browser flow; blocks until redirect received."""
        code_verifier = secrets.token_urlsafe(64)
        code_challenge = create_s256_code_challenge(code_verifier)
        state = secrets.token_urlsafe(16)

        # Start local HTTP server on an OS-assigned port
        received: dict[str, str] = {}

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

            def log_message(self, *args: object) -> None:  # suppress server logs
                pass

        server = HTTPServer(("127.0.0.1", 0), _CallbackHandler)
        port = server.server_address[1]
        redirect_uri = f"http://localhost:{port}/callback"

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

        webbrowser.open(auth_url)
        server.handle_request()
        server.server_close()

        if received.get("state") != state:
            msg = "State mismatch in OAuth callback — possible CSRF attack."
            raise AuthenticationError(msg)

        code = received.get("code", "")
        if not code:
            msg = "No authorization code received in callback."
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

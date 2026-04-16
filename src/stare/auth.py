"""OAuth2 PKCE authentication flow for CERN Keycloak."""

from __future__ import annotations

import json
import secrets
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
from authlib.oauth2.rfc7636 import create_s256_code_challenge
from platformdirs import user_data_dir

from stare.exceptions import AuthenticationError, TokenExpiredError
from stare.settings import StareSettings

_DEFAULT_TOKEN_PATH = Path(user_data_dir("stare")) / "tokens.json"


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
            def do_GET(self) -> None:  # noqa: N802
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
            raise AuthenticationError("State mismatch in OAuth callback — possible CSRF attack.")

        code = received.get("code", "")
        if not code:
            raise AuthenticationError("No authorization code received in callback.")

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
            token_data: dict[str, object] = response.json()

        expires_in = int(token_data.get("expires_in", 3600))
        token_data["expires_at"] = int(time.time()) + expires_in

        self._token_path.parent.mkdir(parents=True, exist_ok=True)
        self._token_path.write_text(json.dumps(token_data))

    def logout(self) -> None:
        """Delete stored tokens."""
        if self._token_path.exists():
            self._token_path.unlink()

    def get_token(self) -> str:
        """Return a valid access token, refreshing if needed."""
        if not self._token_path.exists():
            raise AuthenticationError("Not authenticated. Run `stare login` first.")

        token_data: dict[str, object] = json.loads(self._token_path.read_text())

        # Refresh if expired (or within 60 seconds of expiry)
        if int(token_data.get("expires_at", 0)) < int(time.time()) + 60:
            refresh_token = token_data.get("refresh_token", "")
            if not refresh_token:
                raise TokenExpiredError(
                    "Access token has expired and no refresh token is available. "
                    "Run `stare login` again."
                )
            token_data = self._refresh(str(refresh_token))

        return str(token_data["access_token"])

    def _refresh(self, refresh_token: str) -> dict[str, object]:
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
                new_data: dict[str, object] = response.json()
        except httpx.HTTPStatusError as exc:
            raise TokenExpiredError(
                f"Token refresh failed ({exc.response.status_code}). "
                "Run `stare login` again."
            ) from exc

        expires_in = int(new_data.get("expires_in", 3600))
        new_data["expires_at"] = int(time.time()) + expires_in
        self._token_path.write_text(json.dumps(new_data))
        return new_data

    def is_authenticated(self) -> bool:
        """Return True if a non-expired token is stored."""
        if not self._token_path.exists():
            return False
        try:
            token_data = json.loads(self._token_path.read_text())
            return int(token_data.get("expires_at", 0)) > int(time.time())
        except (json.JSONDecodeError, TypeError, ValueError):
            return False

"""Pydantic models for authentication token data."""

from __future__ import annotations

import time

from pydantic import BaseModel, ConfigDict

from stare.models.common import _Base


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


class JwtClaims(_Base):
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


class TokenInfo(_Base):
    """Token metadata and decoded JWT claims returned by :meth:`~stare.auth.TokenManager.get_token_info`."""

    is_expired: bool
    expires_at: int
    claims: JwtClaims

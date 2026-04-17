"""Pydantic models for authentication token data."""

from __future__ import annotations

import time

from pydantic import BaseModel, ConfigDict, Field

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


class ResourceAccessEntry(_Base):
    """Client-specific role assignments within the resource_access JWT claim."""

    roles: list[str] = Field(default_factory=list)


class JwtClaims(_Base):
    """Decoded JWT payload claims from CERN Keycloak.

    ``extra="allow"`` preserves any claims not listed here so nothing is
    silently dropped when displaying or passing the object around.
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    # Standard JWT registered claims
    jti: str | None = None
    iss: str | None = None
    aud: str | list[str] | None = None
    sub: str | None = None
    typ: str | None = None
    azp: str | None = None
    sid: str | None = None
    exp: int | None = None
    iat: int | None = None
    at_hash: str | None = None

    # OpenID Connect identity claims
    preferred_username: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    name: str | None = None
    email: str | None = None

    # CERN-specific claims
    cern_upn: str | None = None
    cern_mail_upn: str | None = None
    cern_person_id: str | None = None
    cern_identity_id: str | None = None
    cern_preferred_language: str | None = None
    cern_roles: list[str] = Field(default_factory=list)
    resource_access: dict[str, ResourceAccessEntry] = Field(default_factory=dict)

    # Academic identity
    eduperson_orcid: str | None = None


class TokenInfo(_Base):
    """Token metadata and decoded JWT claims returned by :meth:`~stare.auth.TokenManager.get_token_info`."""

    is_expired: bool
    expires_at: int
    claims: JwtClaims

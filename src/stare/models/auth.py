"""Pydantic models for authentication token data."""

from __future__ import annotations

from pydantic import ConfigDict

from stare.models.common import _Base


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

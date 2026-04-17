"""Configuration management for stare via pydantic-settings."""

from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class StareSettings(BaseSettings):
    """Runtime configuration, overridable via ``STARE_*`` environment variables."""

    model_config = SettingsConfigDict(env_prefix="STARE_")

    base_url: str = "https://atlas-glance.cern.ch/atlas/analysis/api"
    auth_url: str = "https://auth.cern.ch/auth/realms/cern/protocol/openid-connect/auth"
    token_url: str = (
        "https://auth.cern.ch/auth/realms/cern/protocol/openid-connect/token"
    )
    client_id: str = "stare"
    scopes: str = "openid"
    # Must match the redirect URI registered with the CERN Keycloak client.
    callback_port: int = 8182
    # Set STARE_VERBOSE=1 to enable DEBUG-level httpx/httpcore request logging.
    verbose: bool = False
    # RFC 8693 token exchange: exchange the PKCE access token for a token
    # scoped to this audience before each API call. Disabled by default; set
    # STARE_EXCHANGE_AUDIENCE=atlas-analysis-api (or similar) to enable.
    exchange_audience: str | None = None
    revocation_url: str = (
        "https://auth.cern.ch/auth/realms/cern/protocol/openid-connect/revoke"
    )
    issuer: str = "https://auth.cern.ch/auth/realms/cern"
    jwks_url: str = (
        "https://auth.cern.ch/auth/realms/cern/protocol/openid-connect/certs"
    )
    # Buffer (seconds) before exchanged token is considered near-expiry and
    # re-exchanged. Default 120s (2 minutes).
    exchange_token_buffer_seconds: int = 120
    # Safety margin (seconds) subtracted from token expiry to account for clock
    # skew between client and server. Default 60s.
    token_expiry_margin_seconds: int = 60
    # CA bundle to use for TLS verification. "Sectigo" is for the production
    # endpoint (atlas-glance.cern.ch); "CERN" is for the staging/dev endpoint
    # (glance-staging01.cern.ch) which still uses the CERN Grid CA.
    # Set STARE_CA_BUNDLE=CERN when pointing STARE_BASE_URL at staging.
    ca_bundle: Literal["Sectigo", "CERN"] = "Sectigo"

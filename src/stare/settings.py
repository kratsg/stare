"""Configuration management for stare via pydantic-settings."""

from __future__ import annotations

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

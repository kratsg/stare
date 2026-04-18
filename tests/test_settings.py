"""Tests for StareSettings configuration."""

from __future__ import annotations

import pytest

from stare.settings import StareSettings

_STARE_ENV_KEYS = [
    "STARE_BASE_URL",
    "STARE_CLIENT_ID",
    "STARE_SCOPES",
    "STARE_AUTH_URL",
    "STARE_TOKEN_URL",
    "STARE_CA_BUNDLE",
    "STARE_EXCHANGE_TOKEN_BUFFER_SECONDS",
    "STARE_TOKEN_EXPIRY_MARGIN_SECONDS",
]


@pytest.fixture(autouse=True)
def clear_stare_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in _STARE_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


class TestStareSettingsDefaults:
    def test_default_base_url(self) -> None:
        s = StareSettings()
        assert s.base_url == "https://atlas-glance.cern.ch/atlas/analysis/api"

    def test_default_client_id(self) -> None:
        s = StareSettings()
        assert s.client_id == "stare"

    def test_default_scopes(self) -> None:
        s = StareSettings()
        assert s.scopes == "openid"

    def test_default_auth_url_contains_cern(self) -> None:
        s = StareSettings()
        assert "auth.cern.ch" in s.auth_url

    def test_default_token_url_contains_cern(self) -> None:
        s = StareSettings()
        assert "auth.cern.ch" in s.token_url

    def test_default_ca_bundle_is_sectigo(self) -> None:
        s = StareSettings()
        assert s.ca_bundle == "Sectigo"


class TestStareSettingsEnvOverrides:
    def test_base_url_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("STARE_BASE_URL", "https://custom.example.com/api")
        s = StareSettings()
        assert s.base_url == "https://custom.example.com/api"

    def test_client_id_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("STARE_CLIENT_ID", "my-client")
        s = StareSettings()
        assert s.client_id == "my-client"

    def test_scopes_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("STARE_SCOPES", "openid profile")
        s = StareSettings()
        assert s.scopes == "openid profile"

    def test_direct_constructor_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("STARE_BASE_URL", "https://env.example.com")
        s = StareSettings(base_url="https://override.example.com")
        assert s.base_url == "https://override.example.com"

    def test_ca_bundle_override_to_cern(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("STARE_CA_BUNDLE", "CERN")
        s = StareSettings()
        assert s.ca_bundle == "CERN"


class TestStareSettingsExpiry:
    def test_default_exchange_token_buffer_seconds(self) -> None:
        s = StareSettings()
        assert s.exchange_token_buffer_seconds == 120

    def test_default_token_expiry_margin_seconds(self) -> None:
        s = StareSettings()
        assert s.token_expiry_margin_seconds == 60

    def test_exchange_token_buffer_seconds_env_override(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("STARE_EXCHANGE_TOKEN_BUFFER_SECONDS", "300")
        s = StareSettings()
        assert s.exchange_token_buffer_seconds == 300

    def test_token_expiry_margin_seconds_env_override(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("STARE_TOKEN_EXPIRY_MARGIN_SECONDS", "90")
        s = StareSettings()
        assert s.token_expiry_margin_seconds == 90

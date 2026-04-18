"""Tests for StareSettings configuration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from stare.settings import StareSettings

if TYPE_CHECKING:
    import pytest


class TestStareSettingsDefaults:
    # pixi.toml sets STARE_BASE_URL to the staging endpoint in the activation
    # environment; monkeypatch removes it so we can test the compiled default.
    def test_default_base_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("STARE_BASE_URL", raising=False)
        s = StareSettings()
        assert s.base_url == "https://atlas-glance.cern.ch/atlas/analysis/api"

    def test_default_client_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("STARE_CLIENT_ID", raising=False)
        s = StareSettings()
        assert s.client_id == "stare"

    def test_default_scopes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("STARE_SCOPES", raising=False)
        s = StareSettings()
        assert s.scopes == "openid"

    def test_default_auth_url_contains_cern(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("STARE_AUTH_URL", raising=False)
        s = StareSettings()
        assert "auth.cern.ch" in s.auth_url

    def test_default_token_url_contains_cern(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("STARE_TOKEN_URL", raising=False)
        s = StareSettings()
        assert "auth.cern.ch" in s.token_url

    def test_default_ca_bundle_is_sectigo(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("STARE_CA_BUNDLE", raising=False)
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

    def test_direct_constructor_override(self) -> None:
        s = StareSettings(base_url="https://override.example.com")
        assert s.base_url == "https://override.example.com"

    def test_ca_bundle_override_to_cern(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("STARE_CA_BUNDLE", "CERN")
        s = StareSettings()
        assert s.ca_bundle == "CERN"


class TestStareSettingsExpiry:
    def test_default_exchange_token_buffer_seconds(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("STARE_EXCHANGE_TOKEN_BUFFER_SECONDS", raising=False)
        s = StareSettings()
        assert s.exchange_token_buffer_seconds == 120

    def test_default_token_expiry_margin_seconds(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("STARE_TOKEN_EXPIRY_MARGIN_SECONDS", raising=False)
        s = StareSettings()
        assert s.token_expiry_margin_seconds == 60

"""Tests for StareSettings configuration."""

from __future__ import annotations

import pytest

from stare.settings import StareSettings


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

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
    @pytest.mark.parametrize(
        "attr,expected",
        [
            ("base_url", "https://atlas-glance.cern.ch/atlas/analysis/api"),
            ("client_id", "stare"),
            ("scopes", "openid"),
            ("ca_bundle", "Sectigo"),
            (
                "auth_url",
                "https://auth.cern.ch/auth/realms/cern/protocol/openid-connect/auth",
            ),
            (
                "token_url",
                "https://auth.cern.ch/auth/realms/cern/protocol/openid-connect/token",
            ),
        ],
    )
    def test_defaults(self, attr: str, expected: str) -> None:
        s = StareSettings()
        assert getattr(s, attr) == expected


class TestStareSettingsEnvOverrides:
    @pytest.mark.parametrize(
        "env_var,value,attr",
        [
            ("STARE_BASE_URL", "https://custom.example.com/api", "base_url"),
            ("STARE_CLIENT_ID", "my-client", "client_id"),
            ("STARE_SCOPES", "openid profile", "scopes"),
            ("STARE_CA_BUNDLE", "CERN", "ca_bundle"),
        ],
    )
    def test_env_override(
        self, monkeypatch: pytest.MonkeyPatch, env_var: str, value: str, attr: str
    ) -> None:
        monkeypatch.setenv(env_var, value)
        s = StareSettings()
        assert getattr(s, attr) == value

    def test_direct_constructor_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("STARE_BASE_URL", "https://env.example.com")
        s = StareSettings(base_url="https://override.example.com")
        assert s.base_url == "https://override.example.com"


class TestStareSettingsExpiry:
    @pytest.mark.parametrize(
        "attr,expected",
        [
            ("exchange_token_buffer_seconds", 120),
            ("token_expiry_margin_seconds", 60),
        ],
    )
    def test_defaults(self, attr: str, expected: int) -> None:
        s = StareSettings()
        assert getattr(s, attr) == expected

    @pytest.mark.parametrize(
        "env_var,attr,value",
        [
            (
                "STARE_EXCHANGE_TOKEN_BUFFER_SECONDS",
                "exchange_token_buffer_seconds",
                300,
            ),
            ("STARE_TOKEN_EXPIRY_MARGIN_SECONDS", "token_expiry_margin_seconds", 90),
        ],
    )
    def test_env_override(
        self, monkeypatch: pytest.MonkeyPatch, env_var: str, attr: str, value: int
    ) -> None:
        monkeypatch.setenv(env_var, str(value))
        s = StareSettings()
        assert getattr(s, attr) == value

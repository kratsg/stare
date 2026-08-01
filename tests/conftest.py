"""Shared pytest fixtures for stare tests."""

from __future__ import annotations

import json
import socket
import time
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from stare.auth import TokenManager
from stare.settings import StareSettings, get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    """Reset the lru_cache'd get_settings() so tests don't leak state via env vars.

    This only guarantees a fresh StareSettings() per test *function* (cleared
    before each test runs). It does NOT help within a single test that
    monkeypatches a STARE_* env var and calls get_settings() more than
    once — the second call still returns the cached first result.
    """
    get_settings.cache_clear()


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--runslow",
        action="store_true",
        default=False,
        help="Run slow integration tests that require live CERN auth",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    if not config.getoption("--runslow"):
        skip_slow = pytest.mark.skip(reason="Pass --runslow to run")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)


def _free_port() -> int:
    """Return an available TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture
def test_settings() -> StareSettings:
    """StareSettings pointing at a test base URL."""
    return StareSettings(
        base_url="https://test-glance.example.com/api",
        auth_url="https://auth.example.com/auth",
        token_url="https://auth.example.com/token",
        revocation_url="https://auth.example.com/revoke",
        issuer="https://auth.example.com/realms/test",
        jwks_url="https://auth.example.com/realms/test/certs",
        client_id="test-client",
        scopes="openid",
        callback_port=_free_port(),
        exchange_audience=None,
        cache_enabled=False,
    )


@pytest.fixture
def tmp_token_path(tmp_path: Path) -> Path:
    """Temporary path for token storage (file not yet created)."""
    return tmp_path / "tokens.json"


@pytest.fixture
def valid_token_data() -> dict[str, object]:
    """A valid (non-expired) token payload dict."""
    return {
        "access_token": "test-access-token",
        "refresh_token": "test-refresh-token",
        "token_type": "Bearer",
        "expires_at": int(time.time()) + 3600,
        "id_token": "test-id-token",
    }


@pytest.fixture
def stored_token_path(
    tmp_token_path: Path, valid_token_data: dict[str, object]
) -> Path:
    """Token path pre-populated with a valid non-expired token."""
    tmp_token_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_token_path.write_text(json.dumps(valid_token_data))
    return tmp_token_path


@pytest.fixture
def mock_token_manager(
    stored_token_path: Path, test_settings: StareSettings
) -> TokenManager:
    """TokenManager backed by a pre-stored valid token (no real auth flow)."""
    return TokenManager(settings=test_settings, token_path=stored_token_path)

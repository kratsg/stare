"""Shared pytest fixtures for stare tests."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from stare.auth import TokenManager
from stare.settings import StareSettings


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


@pytest.fixture
def test_settings() -> StareSettings:
    """StareSettings pointing at a test base URL."""
    return StareSettings(
        base_url="https://test-glance.example.com/api",
        auth_url="https://auth.example.com/auth",
        token_url="https://auth.example.com/token",
        client_id="test-client",
        scopes="openid",
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

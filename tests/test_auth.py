"""Tests for stare.auth.TokenManager."""

from __future__ import annotations

import contextlib
import json
import threading
import time
import urllib.request
from typing import TYPE_CHECKING
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx

from stare.auth import TokenManager
from stare.exceptions import AuthenticationError, TokenExpiredError

if TYPE_CHECKING:
    from pathlib import Path

    from stare.settings import StareSettings

# ---------------------------------------------------------------------------
# logout
# ---------------------------------------------------------------------------


def test_logout_removes_token_file(
    stored_token_path: Path, test_settings: StareSettings
) -> None:
    manager = TokenManager(settings=test_settings, token_path=stored_token_path)
    assert stored_token_path.exists()
    manager.logout()
    assert not stored_token_path.exists()


def test_logout_no_op_when_no_token(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
    assert not tmp_token_path.exists()
    manager.logout()  # must not raise


# ---------------------------------------------------------------------------
# is_authenticated
# ---------------------------------------------------------------------------


def test_is_authenticated_false_when_no_file(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
    assert manager.is_authenticated() is False


def test_is_authenticated_true_with_valid_token(
    stored_token_path: Path, test_settings: StareSettings
) -> None:
    manager = TokenManager(settings=test_settings, token_path=stored_token_path)
    assert manager.is_authenticated() is True


def test_is_authenticated_false_with_expired_token(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    expired = {
        "access_token": "old",
        "refresh_token": "rt",
        "token_type": "Bearer",
        "expires_at": int(time.time()) - 10,
        "id_token": "id",
    }
    tmp_token_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_token_path.write_text(json.dumps(expired))
    manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
    assert manager.is_authenticated() is False


def test_is_authenticated_false_with_corrupt_file(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    tmp_token_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_token_path.write_text("not-json{{{")
    manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
    assert manager.is_authenticated() is False


# ---------------------------------------------------------------------------
# get_token
# ---------------------------------------------------------------------------


def test_get_token_returns_access_token(
    stored_token_path: Path, test_settings: StareSettings
) -> None:
    manager = TokenManager(settings=test_settings, token_path=stored_token_path)
    assert manager.get_token() == "test-access-token"


def test_get_token_raises_when_no_token(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
    with pytest.raises(AuthenticationError):
        manager.get_token()


def test_get_token_refreshes_on_expiry(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    expired = {
        "access_token": "old-access",
        "refresh_token": "old-refresh",
        "token_type": "Bearer",
        "expires_at": int(time.time()) - 10,
        "id_token": "old-id",
    }
    tmp_token_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_token_path.write_text(json.dumps(expired))

    new_tokens = {
        "access_token": "new-access",
        "refresh_token": "new-refresh",
        "token_type": "Bearer",
        "expires_in": 3600,
        "id_token": "new-id",
    }

    with respx.mock:
        respx.post(test_settings.token_url).mock(
            return_value=httpx.Response(200, json=new_tokens)
        )
        manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
        token = manager.get_token()

    assert token == "new-access"
    stored = json.loads(tmp_token_path.read_text())
    assert stored["access_token"] == "new-access"
    assert stored["refresh_token"] == "new-refresh"
    assert stored["expires_at"] > int(time.time())


def test_get_token_raises_on_refresh_failure(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    expired = {
        "access_token": "old",
        "refresh_token": "bad-refresh",
        "token_type": "Bearer",
        "expires_at": int(time.time()) - 10,
        "id_token": "id",
    }
    tmp_token_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_token_path.write_text(json.dumps(expired))

    with respx.mock:
        respx.post(test_settings.token_url).mock(
            return_value=httpx.Response(401, json={"error": "invalid_grant"})
        )
        manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
        with pytest.raises(TokenExpiredError):
            manager.get_token()


def test_get_token_raises_when_no_refresh_token(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    expired = {
        "access_token": "old",
        "token_type": "Bearer",
        "expires_at": int(time.time()) - 10,
    }
    tmp_token_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_token_path.write_text(json.dumps(expired))

    manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
    with pytest.raises(TokenExpiredError):
        manager.get_token()


# ---------------------------------------------------------------------------
# login (PKCE flow)
# ---------------------------------------------------------------------------


def _make_callback_thread(captured_url: dict[str, str]) -> threading.Thread:
    """Background thread: wait for browser open, then send fake callback."""

    def _run() -> None:
        # Wait until webbrowser.open has been called and URL captured
        deadline = time.time() + 5.0
        while "url" not in captured_url and time.time() < deadline:
            time.sleep(0.01)

        url = captured_url.get("url", "")
        if not url:
            return

        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        state = params.get("state", [""])[0]
        redirect_uri = params.get("redirect_uri", [""])[0]
        if not redirect_uri:
            return

        port = urlparse(redirect_uri).port
        callback_url = (
            f"http://127.0.0.1:{port}/callback?code=fake-auth-code&state={state}"
        )
        # Small delay to ensure the server is listening
        time.sleep(0.05)
        with contextlib.suppress(Exception):
            urllib.request.urlopen(callback_url, timeout=5)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t


def test_login_stores_tokens(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    captured_url: dict[str, str] = {}

    def _fake_browser(url: str) -> bool:
        captured_url["url"] = url
        return True

    new_tokens = {
        "access_token": "login-access",
        "refresh_token": "login-refresh",
        "token_type": "Bearer",
        "expires_in": 3600,
        "id_token": "login-id",
    }

    callback_thread = _make_callback_thread(captured_url)

    with respx.mock:
        respx.post(test_settings.token_url).mock(
            return_value=httpx.Response(200, json=new_tokens)
        )
        with patch("stare.auth.webbrowser.open", side_effect=_fake_browser):
            manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
            manager.login()

    callback_thread.join(timeout=5.0)

    assert tmp_token_path.exists()
    stored = json.loads(tmp_token_path.read_text())
    assert stored["access_token"] == "login-access"
    assert stored["refresh_token"] == "login-refresh"
    assert stored["expires_at"] > int(time.time())


def test_login_opens_browser_with_pkce_params(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    captured_url: dict[str, str] = {}

    def _fake_browser(url: str) -> bool:
        captured_url["url"] = url
        return True

    new_tokens = {
        "access_token": "a",
        "refresh_token": "r",
        "token_type": "Bearer",
        "expires_in": 3600,
    }

    callback_thread = _make_callback_thread(captured_url)

    with respx.mock:
        respx.post(test_settings.token_url).mock(
            return_value=httpx.Response(200, json=new_tokens)
        )
        with patch("stare.auth.webbrowser.open", side_effect=_fake_browser):
            manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
            manager.login()

    callback_thread.join(timeout=5.0)

    assert "url" in captured_url
    parsed = urlparse(captured_url["url"])
    assert parsed.scheme + "://" + parsed.netloc + parsed.path == test_settings.auth_url
    params = parse_qs(parsed.query)
    assert params["response_type"] == ["code"]
    assert params["client_id"] == [test_settings.client_id]
    assert params["code_challenge_method"] == ["S256"]
    assert "code_challenge" in params
    assert "state" in params
    assert "redirect_uri" in params


def test_login_calls_on_url_ready_callback(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    captured_url: dict[str, str] = {}
    ready_urls: list[str] = []

    def _fake_browser(url: str) -> bool:
        captured_url["url"] = url
        return True

    def _on_url_ready(url: str) -> None:
        ready_urls.append(url)

    new_tokens = {
        "access_token": "cb-access",
        "refresh_token": "cb-refresh",
        "token_type": "Bearer",
        "expires_in": 3600,
    }

    callback_thread = _make_callback_thread(captured_url)

    with respx.mock:
        respx.post(test_settings.token_url).mock(
            return_value=httpx.Response(200, json=new_tokens)
        )
        with patch("stare.auth.webbrowser.open", side_effect=_fake_browser):
            manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
            manager.login(on_url_ready=_on_url_ready)

    callback_thread.join(timeout=5.0)

    assert len(ready_urls) == 1
    assert test_settings.auth_url in ready_urls[0]
    assert "code_challenge" in ready_urls[0]


def test_login_uses_manual_code_fallback(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    """get_manual_code() is used when the browser redirect doesn't arrive."""

    def _fake_browser(_url: str) -> bool:
        return True  # pretend to open; no callback will be sent

    def _get_manual_code() -> str | None:
        time.sleep(0.05)  # small delay simulating user typing
        return "manual-auth-code"

    new_tokens = {
        "access_token": "manual-access",
        "refresh_token": "manual-refresh",
        "token_type": "Bearer",
        "expires_in": 3600,
    }

    with respx.mock:
        respx.post(test_settings.token_url).mock(
            return_value=httpx.Response(200, json=new_tokens)
        )
        with patch("stare.auth.webbrowser.open", side_effect=_fake_browser):
            manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
            manager.login(get_manual_code=_get_manual_code)

    assert tmp_token_path.exists()
    stored = json.loads(tmp_token_path.read_text())
    assert stored["access_token"] == "manual-access"
    assert stored["refresh_token"] == "manual-refresh"

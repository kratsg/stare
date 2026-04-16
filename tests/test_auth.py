"""Tests for stare.auth.TokenManager."""

from __future__ import annotations

import base64
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

from stare.auth import TokenManager, _decode_jwt_payload
from stare.exceptions import AuthenticationError, TokenExpiredError
from stare.models.auth import JwtClaims, TokenInfo

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from stare.settings import StareSettings


def _make_jwt(payload: Mapping[str, object]) -> str:
    """Build a minimal JWT with the given payload (signature is a fake placeholder)."""
    header_b64 = base64.urlsafe_b64encode(b'{"alg":"RS256"}').rstrip(b"=").decode()
    payload_b64 = (
        base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    )
    return f"{header_b64}.{payload_b64}.fakesig"


# ---------------------------------------------------------------------------
# _decode_jwt_payload
# ---------------------------------------------------------------------------


def test_decode_jwt_payload_returns_known_claims() -> None:
    payload = {
        "sub": "abc123",
        "preferred_username": "kratsg",
        "name": "Test User",
        "email": "test@cern.ch",
        "exp": 9999999999,
        "iat": 1000000000,
    }
    claims = _decode_jwt_payload(_make_jwt(payload))
    assert isinstance(claims, JwtClaims)
    assert claims.sub == "abc123"
    assert claims.preferred_username == "kratsg"
    assert claims.name == "Test User"
    assert claims.email == "test@cern.ch"
    assert claims.exp == 9999999999
    assert claims.iat == 1000000000


def test_decode_jwt_payload_preserves_extra_claims() -> None:
    payload = {"sub": "abc", "custom_claim": "custom_value"}
    claims = _decode_jwt_payload(_make_jwt(payload))
    assert claims.sub == "abc"
    assert getattr(claims, "custom_claim", None) == "custom_value"


def test_decode_jwt_payload_returns_empty_on_missing_dot() -> None:
    # No dots → IndexError on [1] → returns empty JwtClaims
    claims = _decode_jwt_payload("invalid-jwt")
    assert isinstance(claims, JwtClaims)
    assert claims.sub is None
    assert claims.preferred_username is None


def test_decode_jwt_payload_returns_empty_on_non_json_payload() -> None:
    # Middle segment decodes to non-JSON bytes
    bad = "header." + base64.urlsafe_b64encode(b"not-json").decode() + ".sig"
    claims = _decode_jwt_payload(bad)
    assert isinstance(claims, JwtClaims)
    assert claims.sub is None


# ---------------------------------------------------------------------------
# get_token_info
# ---------------------------------------------------------------------------


def test_get_token_info_returns_none_when_no_file(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
    assert manager.get_token_info() is None


def test_get_token_info_returns_token_info(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    payload = {"sub": "abc123", "preferred_username": "kratsg"}
    stored = {
        "access_token": "at",
        "id_token": _make_jwt(payload),
        "token_type": "Bearer",
        "expires_at": int(time.time()) + 3600,
    }
    tmp_token_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_token_path.write_text(json.dumps(stored))
    manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
    info = manager.get_token_info()
    assert info is not None
    assert isinstance(info, TokenInfo)
    assert info.is_expired is False
    assert info.claims.sub == "abc123"
    assert info.claims.preferred_username == "kratsg"


def test_get_token_info_prefers_id_token_over_access_token(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    stored = {
        "access_token": _make_jwt({"sub": "from-access"}),
        "id_token": _make_jwt({"sub": "from-id", "preferred_username": "kratsg"}),
        "token_type": "Bearer",
        "expires_at": int(time.time()) + 3600,
    }
    tmp_token_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_token_path.write_text(json.dumps(stored))
    manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
    info = manager.get_token_info()
    assert info is not None
    assert info.claims.sub == "from-id"


def test_get_token_info_falls_back_to_access_token(
    tmp_token_path: Path, test_settings: StareSettings
) -> None:
    stored = {
        "access_token": _make_jwt(
            {"sub": "from-access", "preferred_username": "kratsg"}
        ),
        "token_type": "Bearer",
        "expires_at": int(time.time()) + 3600,
    }
    tmp_token_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_token_path.write_text(json.dumps(stored))
    manager = TokenManager(settings=test_settings, token_path=tmp_token_path)
    info = manager.get_token_info()
    assert info is not None
    assert info.claims.sub == "from-access"


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

"""Tests for HTTP cache settings and the stare cache CLI subcommands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import platformdirs
import pytest
from typer.testing import CliRunner

from stare.cli import app
from stare.models import AnalysisSearchResult
from stare.settings import StareSettings

runner = CliRunner()


def _make_settings(**kw: object) -> StareSettings:
    return StareSettings(  # type: ignore[arg-type]
        base_url="https://example.com",
        auth_url="https://example.com/auth",
        token_url="https://example.com/token",
        revocation_url="https://example.com/revoke",
        issuer="https://example.com",
        jwks_url="https://example.com/certs",
        **kw,
    )


def _cache_settings(tmp_path: Path, **kw: object) -> StareSettings:
    return _make_settings(cache_dir=tmp_path / "cache", **kw)


# ---------------------------------------------------------------------------
# StareSettings cache defaults
# ---------------------------------------------------------------------------


class TestCacheSettings:
    def test_defaults(self) -> None:
        s = _make_settings()
        assert s.cache_enabled is True
        assert s.cache_ttl_seconds == 28800

    def test_cache_disabled(self) -> None:
        s = _make_settings(cache_enabled=False)
        assert s.cache_enabled is False

    def test_cache_ttl_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("STARE_CACHE_TTL_SECONDS", "60")
        s = _make_settings()
        assert s.cache_ttl_seconds == 60

    def test_get_cache_dir_custom(self, tmp_path: Path) -> None:
        s = _make_settings(cache_dir=tmp_path / "stare_cache")
        assert s.get_cache_dir() == tmp_path / "stare_cache"

    def test_get_cache_dir_default(self) -> None:
        s = _make_settings(cache_dir=None)
        assert s.get_cache_dir() == Path(platformdirs.user_cache_dir("stare"))


def test_cache_dir_env_var(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    custom = str(tmp_path / "custom_cache")
    monkeypatch.setenv("STARE_CACHE_DIR", custom)
    s = _make_settings()
    assert s.get_cache_dir() == Path(custom)


def test_cache_enabled_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STARE_CACHE_ENABLED", "false")
    s = _make_settings()
    assert s.cache_enabled is False


# ---------------------------------------------------------------------------
# stare cache info
# ---------------------------------------------------------------------------


class TestCacheInfoCommand:
    def test_shows_cache_info(self, tmp_path: Path) -> None:
        settings = _cache_settings(tmp_path)
        with patch("stare.cli._make_settings", return_value=settings):
            result = runner.invoke(app, ["cache", "info"])
        assert result.exit_code == 0
        # Normalize output: Rich may wrap long paths across lines.
        normalized = result.output.replace("\n", "")
        assert str(settings.get_cache_dir()) in normalized
        assert "28800" in result.output

    def test_shows_zero_size_when_no_db(self, tmp_path: Path) -> None:
        settings = _cache_settings(tmp_path)
        with patch("stare.cli._make_settings", return_value=settings):
            result = runner.invoke(app, ["cache", "info"])
        assert result.exit_code == 0
        assert "0 bytes" in result.output

    def test_shows_nonzero_size_when_db_exists(self, tmp_path: Path) -> None:
        settings = _cache_settings(tmp_path)
        db_path = settings.get_cache_dir() / "cache.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db_path.write_bytes(b"x" * 1024)
        with patch("stare.cli._make_settings", return_value=settings):
            result = runner.invoke(app, ["cache", "info"])
        assert result.exit_code == 0
        assert "1024" in result.output


# ---------------------------------------------------------------------------
# stare cache clear
# ---------------------------------------------------------------------------


class TestCacheClearCommand:
    def test_clear_removes_db(self, tmp_path: Path) -> None:
        settings = _cache_settings(tmp_path)
        db_path = settings.get_cache_dir() / "cache.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db_path.write_bytes(b"data")
        with patch("stare.cli._make_settings", return_value=settings):
            result = runner.invoke(app, ["cache", "clear", "--yes"])
        assert result.exit_code == 0
        assert not db_path.exists()
        assert "cleared" in result.output.lower()

    def test_clear_when_no_db_is_harmless(self, tmp_path: Path) -> None:
        settings = _cache_settings(tmp_path)
        with patch("stare.cli._make_settings", return_value=settings):
            result = runner.invoke(app, ["cache", "clear", "--yes"])
        assert result.exit_code == 0
        assert "nothing to clear" in result.output.lower()


# ---------------------------------------------------------------------------
# --no-cache flag
# ---------------------------------------------------------------------------


class TestNoCacheFlag:
    def test_no_cache_flag_is_accepted(self) -> None:
        g = MagicMock()
        g.analyses.search.return_value = AnalysisSearchResult.model_validate(
            {"totalRows": 0, "results": []}
        )
        with patch("stare.cli._make_glance", return_value=g):
            result = runner.invoke(app, ["analysis", "search", "--no-cache"])
        assert result.exit_code == 0

    def test_no_cache_calls_make_glance_with_flag(self) -> None:
        g = MagicMock()
        g.analyses.search.return_value = AnalysisSearchResult.model_validate(
            {"totalRows": 0, "results": []}
        )
        with patch("stare.cli._make_glance", return_value=g) as mock_make:
            runner.invoke(app, ["analysis", "search", "--no-cache"])
        mock_make.assert_called_once_with(no_cache=True)

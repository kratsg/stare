"""Tests for HTTP cache settings and the stare cache CLI subcommands."""

from __future__ import annotations

import sqlite3
import time
from contextlib import closing
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import httpx
import platformdirs
import respx
from typer.testing import CliRunner

if TYPE_CHECKING:
    import pytest

from stare import Glance
from stare.cli import app, sizeof_fmt
from stare.models import AnalysisSearchResult
from stare.settings import StareSettings

runner = CliRunner()


_BASE_KWARGS = {
    "base_url": "https://example.com",
    "auth_url": "https://example.com/auth",
    "token_url": "https://example.com/token",
    "revocation_url": "https://example.com/revoke",
    "issuer": "https://example.com",
    "jwks_url": "https://example.com/certs",
}


def _make_settings(**kw: object) -> StareSettings:
    return StareSettings.model_validate({**_BASE_KWARGS, **kw})


def _cache_settings(tmp_path: Path, **kw: object) -> StareSettings:
    return _make_settings(cache_dir=tmp_path / "cache", **kw)


# ---------------------------------------------------------------------------
# sizeof_fmt
# ---------------------------------------------------------------------------


class TestSizeofFmt:
    def test_zero(self) -> None:
        assert sizeof_fmt(0) == "0.0B"

    def test_sub_kibibyte(self) -> None:
        assert sizeof_fmt(512) == "512.0B"

    def test_exactly_one_kibibyte(self) -> None:
        assert sizeof_fmt(1024) == "1.0KiB"

    def test_mebibyte(self) -> None:
        assert sizeof_fmt(1024 * 1024) == "1.0MiB"


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

    def test_get_cache_db_path(self, tmp_path: Path) -> None:
        # hishel 2.x refuses to open a hishel 1.x database, so the 2.x cache
        # lives in its own file next to the legacy cache.db
        s = _make_settings(cache_dir=tmp_path / "stare_cache")
        assert s.get_cache_db_path() == tmp_path / "stare_cache" / "cache-v2.db"


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
        with patch("stare.cli.utils.make_settings", return_value=settings):
            result = runner.invoke(app, ["cache", "info"])
        assert result.exit_code == 0
        # Normalize output: Rich may wrap long paths across lines.
        normalized = result.output.replace("\n", "")
        assert str(settings.get_cache_dir()) in normalized
        assert "28800" in result.output

    def test_shows_database_path(self, tmp_path: Path) -> None:
        settings = _cache_settings(tmp_path)
        with patch("stare.cli.utils.make_settings", return_value=settings):
            result = runner.invoke(app, ["cache", "info"])
        assert result.exit_code == 0
        # Normalize output: Rich may wrap long paths across lines.
        normalized = result.output.replace("\n", "")
        assert str(settings.get_cache_db_path()) in normalized

    def test_shows_zero_size_when_no_db(self, tmp_path: Path) -> None:
        settings = _cache_settings(tmp_path)
        with patch("stare.cli.utils.make_settings", return_value=settings):
            result = runner.invoke(app, ["cache", "info"])
        assert result.exit_code == 0
        assert "0 bytes" in result.output

    def test_shows_nonzero_size_when_db_exists(self, tmp_path: Path) -> None:
        settings = _cache_settings(tmp_path)
        db_path = settings.get_cache_db_path()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db_path.write_bytes(b"x" * 1024)
        with patch("stare.cli.utils.make_settings", return_value=settings):
            result = runner.invoke(app, ["cache", "info"])
        assert result.exit_code == 0
        assert "1.0KiB" in result.output
        assert "1024" in result.output  # raw bytes visible in parens


# ---------------------------------------------------------------------------
# stare cache clear
# ---------------------------------------------------------------------------


class TestCacheClearCommand:
    def test_clear_removes_db(self, tmp_path: Path) -> None:
        settings = _cache_settings(tmp_path)
        db_path = settings.get_cache_db_path()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db_path.write_bytes(b"data")
        with patch("stare.cli.utils.make_settings", return_value=settings):
            result = runner.invoke(app, ["cache", "clear", "--yes"])
        assert result.exit_code == 0
        assert not db_path.exists()
        assert "cleared" in result.output.lower()

    def test_clear_removes_legacy_db(self, tmp_path: Path) -> None:
        # the hishel 1.x cache file is never read again, so clear drops it too
        settings = _cache_settings(tmp_path)
        legacy = settings.get_cache_dir() / "cache.db"
        legacy.parent.mkdir(parents=True, exist_ok=True)
        legacy.write_bytes(b"data")
        with patch("stare.cli.utils.make_settings", return_value=settings):
            result = runner.invoke(app, ["cache", "clear", "--yes"])
        assert result.exit_code == 0
        assert not legacy.exists()
        assert "cleared" in result.output.lower()

    def test_clear_removes_sqlite_sidecar_files(self, tmp_path: Path) -> None:
        # SQLite in WAL mode keeps -wal/-shm files beside the database until a
        # clean close; after a crash they stay, and a leftover WAL could be
        # replayed into the next database created under the same name
        settings = _cache_settings(tmp_path)
        db_path = settings.get_cache_db_path()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        for suffix in ("", "-wal", "-shm"):
            Path(f"{db_path}{suffix}").write_bytes(b"data")
        with patch("stare.cli.utils.make_settings", return_value=settings):
            result = runner.invoke(app, ["cache", "clear", "--yes"])
        assert result.exit_code == 0
        assert list(settings.get_cache_dir().glob(f"{db_path.name}*")) == []

    def test_clear_when_no_db_is_harmless(self, tmp_path: Path) -> None:
        settings = _cache_settings(tmp_path)
        with patch("stare.cli.utils.make_settings", return_value=settings):
            result = runner.invoke(app, ["cache", "clear", "--yes"])
        assert result.exit_code == 0
        assert "nothing to clear" in result.output.lower()


# ---------------------------------------------------------------------------
# --no-cache flag
# ---------------------------------------------------------------------------


class TestNoCacheFlag:
    def test_no_cache_flag_is_accepted(self) -> None:
        g = MagicMock()
        # Like the real Glance, entering the context manager yields the same client.
        g.__enter__.return_value = g
        g.analyses.search.return_value = AnalysisSearchResult.model_validate(
            {"numberOfResults": 1, "results": []}
        )
        with patch("stare.cli.utils.make_glance", return_value=g):
            result = runner.invoke(app, ["analysis", "search", "--no-cache"])
        assert result.exit_code == 0

    def test_no_cache_calls_make_glance_with_flag(self) -> None:
        g = MagicMock()
        # Like the real Glance, entering the context manager yields the same client.
        g.__enter__.return_value = g
        g.analyses.search.return_value = AnalysisSearchResult.model_validate(
            {"numberOfResults": 1, "results": []}
        )
        with patch("stare.cli.utils.make_glance", return_value=g) as mock_make:
            runner.invoke(app, ["analysis", "search", "--no-cache"])
        mock_make.assert_called_once_with(no_cache=True)


# ---------------------------------------------------------------------------
# Response caching through the Glance client
# ---------------------------------------------------------------------------

_EMPTY_SEARCH = {"numberOfResults": 0, "results": []}


def _search_twice(settings: StareSettings) -> int:
    """Run the same analysis search twice; return how many reached the network."""
    with respx.mock(base_url=settings.base_url) as rx:
        route = rx.get("/searchAnalysis").mock(
            return_value=httpx.Response(200, json=_EMPTY_SEARCH)
        )
        with Glance(settings=settings, token="fake-token") as g:
            g.analyses.search(query="referenceCode = ANA-TEST-2026-01")
            g.analyses.search(query="referenceCode = ANA-TEST-2026-01")
        return route.call_count


class TestGlanceResponseCache:
    def test_repeated_get_is_served_from_cache(self, tmp_path: Path) -> None:
        # Glance sends no caching headers; the cache still serves the repeat
        assert _search_twice(_cache_settings(tmp_path)) == 1

    def test_cache_written_to_db_path(self, tmp_path: Path) -> None:
        settings = _cache_settings(tmp_path)
        _search_twice(settings)
        assert settings.get_cache_db_path().exists()

    def test_disabled_cache_always_hits_network(self, tmp_path: Path) -> None:
        assert _search_twice(_cache_settings(tmp_path, cache_enabled=False)) == 2

    def test_entry_expires_after_ttl(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        settings = _cache_settings(tmp_path, cache_ttl_seconds=60)
        with respx.mock(base_url=settings.base_url) as rx:
            route = rx.get("/searchAnalysis").mock(
                return_value=httpx.Response(200, json=_EMPTY_SEARCH)
            )
            with Glance(settings=settings, token="fake-token") as g:
                g.analyses.search(query="referenceCode = ANA-TEST-2026-01")
                # jump the wall clock past the TTL instead of sleeping
                real_time = time.time
                monkeypatch.setattr(time, "time", lambda: real_time() + 61)
                g.analyses.search(query="referenceCode = ANA-TEST-2026-01")
        assert route.call_count == 2

    def test_legacy_hishel1_db_does_not_break_requests(self, tmp_path: Path) -> None:
        # a cache.db left by hishel 1.x has a schema hishel 2.x refuses to
        # open; it must be ignored rather than fail every request
        settings = _cache_settings(tmp_path)
        legacy = settings.get_cache_dir() / "cache.db"
        legacy.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(legacy)) as conn:
            conn.execute(
                "CREATE TABLE entries (id BLOB PRIMARY KEY, cache_key BLOB, "
                "data BLOB, created_at REAL, deleted_at REAL)"
            )
        assert _search_twice(settings) == 1

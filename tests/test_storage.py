"""Tests for stare.storage."""

from __future__ import annotations

import time
from pathlib import Path

from stare.models.auth import _StoredToken
from stare.storage import FileTokenStorage


def _make_stored_token(
    access_token: str = "at",
    refresh_token: str | None = "rt",
) -> _StoredToken:
    return _StoredToken(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        expires_at=int(time.time()) + 3600,
    )


def test_file_storage_not_exists_initially(tmp_path: Path) -> None:
    storage = FileTokenStorage(tmp_path / "tokens.json")
    assert storage.exists() is False


def test_file_storage_load_returns_none_when_absent(tmp_path: Path) -> None:
    storage = FileTokenStorage(tmp_path / "tokens.json")
    assert storage.load() is None


def test_file_storage_save_creates_file(tmp_path: Path) -> None:
    path = tmp_path / "tokens.json"
    storage = FileTokenStorage(path)
    storage.save(_make_stored_token())
    assert path.exists()


def test_file_storage_load_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "tokens.json"
    storage = FileTokenStorage(path)
    token = _make_stored_token(access_token="round-trip-at")
    storage.save(token)
    loaded = storage.load()
    assert loaded is not None
    assert loaded.access_token == "round-trip-at"
    assert loaded.refresh_token == "rt"


def test_file_storage_exists_true_after_save(tmp_path: Path) -> None:
    storage = FileTokenStorage(tmp_path / "tokens.json")
    assert not storage.exists()
    storage.save(_make_stored_token())
    assert storage.exists()


def test_file_storage_delete_removes_file(tmp_path: Path) -> None:
    path = tmp_path / "tokens.json"
    storage = FileTokenStorage(path)
    storage.save(_make_stored_token())
    storage.delete()
    assert not path.exists()
    assert not storage.exists()


def test_file_storage_delete_noop_when_absent(tmp_path: Path) -> None:
    storage = FileTokenStorage(tmp_path / "tokens.json")
    storage.delete()  # must not raise


def test_file_storage_save_creates_parent_directories(tmp_path: Path) -> None:
    path = tmp_path / "deep" / "nested" / "tokens.json"
    storage = FileTokenStorage(path)
    storage.save(_make_stored_token(access_token="nested-at"))
    assert path.exists()


def test_file_storage_lock_path(tmp_path: Path) -> None:
    path = tmp_path / "tokens.json"
    storage = FileTokenStorage(path)
    assert storage.lock_path == tmp_path / "tokens.lock"

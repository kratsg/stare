"""Tests for stare.storage."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import keyring.errors
import pytest
from keyring.backends.fail import Keyring as FailKeyring
from platformdirs import user_data_dir

from stare.models.auth import _StoredToken
from stare.storage import FileTokenStorage, KeyringTokenStorage, get_default_storage


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


# ---------------------------------------------------------------------------
# FileTokenStorage
# ---------------------------------------------------------------------------


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


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX permission bits")
def test_file_storage_save_creates_file_with_0600_perms(tmp_path: Path) -> None:
    path = tmp_path / "tokens.json"
    storage = FileTokenStorage(path)
    storage.save(_make_stored_token())
    assert path.stat().st_mode & 0o777 == 0o600


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


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX permission bits")
def test_file_storage_save_perms_0600_despite_permissive_umask(tmp_path: Path) -> None:
    """Even with a wide-open umask, the file must never be created wider than 0600."""
    path = tmp_path / "tokens.json"
    storage = FileTokenStorage(path)

    old_umask = os.umask(0o000)
    try:
        storage.save(_make_stored_token())
    finally:
        os.umask(old_umask)
    assert path.stat().st_mode & 0o777 == 0o600


def test_file_storage_save_leaves_no_temp_file_behind(tmp_path: Path) -> None:
    path = tmp_path / "tokens.json"
    storage = FileTokenStorage(path)
    storage.save(_make_stored_token())
    assert {p.name for p in tmp_path.iterdir()} == {"tokens.json"}


def test_file_storage_save_overwrite_is_atomic_replace(tmp_path: Path) -> None:
    """save() must replace the target via a single atomic rename, not truncate-in-place."""
    path = tmp_path / "tokens.json"
    storage = FileTokenStorage(path)
    storage.save(_make_stored_token(access_token="first"))
    first_inode = path.stat().st_ino

    with patch(
        "pathlib.Path.replace", side_effect=Path.replace, autospec=True
    ) as mock_replace:
        storage.save(_make_stored_token(access_token="second"))

    mock_replace.assert_called_once()
    tmp_arg, target_arg = mock_replace.call_args.args
    assert target_arg == path
    assert tmp_arg.parent == path.parent
    # A real rename produces a new inode; content is never edited in place.
    assert path.stat().st_ino != first_inode
    loaded = storage.load()
    assert loaded is not None
    assert loaded.access_token == "second"


def test_file_storage_load_uses_utf8_encoding(tmp_path: Path) -> None:
    """load() must not rely on locale-dependent default encoding (see save(), which pins utf-8)."""
    path = tmp_path / "tokens.json"
    path.write_text(_make_stored_token().model_dump_json(), encoding="utf-8")
    storage = FileTokenStorage(path)
    with patch(
        "pathlib.Path.read_text", side_effect=Path.read_text, autospec=True
    ) as mock_read_text:
        storage.load()
    mock_read_text.assert_called_once_with(path, encoding="utf-8")


# ---------------------------------------------------------------------------
# KeyringTokenStorage
# ---------------------------------------------------------------------------


def test_keyring_storage_load_returns_none_when_empty() -> None:
    with patch("keyring.get_password", return_value=None):
        storage = KeyringTokenStorage()
        assert storage.load() is None


def test_keyring_storage_load_returns_token() -> None:
    token = _make_stored_token("ks-at")
    with patch("keyring.get_password", return_value=token.model_dump_json()):
        storage = KeyringTokenStorage()
        loaded = storage.load()
    assert loaded is not None
    assert loaded.access_token == "ks-at"


def test_keyring_storage_save_calls_set_password() -> None:
    token = _make_stored_token("ks-save")
    with patch("keyring.set_password") as mock_set:
        KeyringTokenStorage().save(token)
    mock_set.assert_called_once_with(
        KeyringTokenStorage.SERVICE_NAME,
        KeyringTokenStorage.ENTRY_KEY,
        token.model_dump_json(),
    )


def test_keyring_storage_exists_true() -> None:
    token = _make_stored_token()
    with patch("keyring.get_password", return_value=token.model_dump_json()):
        assert KeyringTokenStorage().exists() is True


def test_keyring_storage_exists_false() -> None:
    with patch("keyring.get_password", return_value=None):
        assert KeyringTokenStorage().exists() is False


def test_keyring_storage_delete_calls_delete_password() -> None:
    with patch("keyring.delete_password") as mock_del:
        KeyringTokenStorage().delete()
    mock_del.assert_called_once_with(
        KeyringTokenStorage.SERVICE_NAME, KeyringTokenStorage.ENTRY_KEY
    )


def test_keyring_storage_delete_noop_on_missing_entry() -> None:
    with patch(
        "keyring.delete_password",
        side_effect=keyring.errors.PasswordDeleteError,
    ):
        KeyringTokenStorage().delete()  # must not raise


def test_keyring_storage_lock_path() -> None:
    storage = KeyringTokenStorage()
    assert storage.lock_path == Path(user_data_dir("stare")) / "tokens.lock"


# ---------------------------------------------------------------------------
# KeyringTokenStorage.migrate_from_file
# ---------------------------------------------------------------------------


def test_keyring_migrate_moves_file_tokens_to_keyring(tmp_path: Path) -> None:
    path = tmp_path / "tokens.json"
    token = _make_stored_token("migrate-at")
    FileTokenStorage(path).save(token)

    saved: dict[tuple[str, str], str] = {}

    def _fake_get(service: str, username: str) -> str | None:
        return saved.get((service, username))

    def _fake_set(service: str, username: str, password: str) -> None:
        saved[(service, username)] = password

    with (
        patch("keyring.get_password", side_effect=_fake_get),
        patch("keyring.set_password", side_effect=_fake_set),
    ):
        KeyringTokenStorage().migrate_from_file(path)

    assert (KeyringTokenStorage.SERVICE_NAME, KeyringTokenStorage.ENTRY_KEY) in saved
    assert not path.exists()


def test_keyring_migrate_noop_when_keyring_already_populated(tmp_path: Path) -> None:
    path = tmp_path / "tokens.json"
    FileTokenStorage(path).save(_make_stored_token("file-at"))

    with (
        patch(
            "keyring.get_password", return_value=_make_stored_token().model_dump_json()
        ),
        patch("keyring.set_password") as mock_set,
    ):
        KeyringTokenStorage().migrate_from_file(path)
    mock_set.assert_not_called()
    assert path.exists()  # file NOT deleted


def test_keyring_migrate_noop_when_file_absent(tmp_path: Path) -> None:
    path = tmp_path / "tokens.json"
    with (
        patch("keyring.get_password", return_value=None),
        patch("keyring.set_password") as mock_set,
    ):
        KeyringTokenStorage().migrate_from_file(path)
    mock_set.assert_not_called()


# ---------------------------------------------------------------------------
# get_default_storage
# ---------------------------------------------------------------------------


def test_get_default_storage_returns_file_when_fail_keyring() -> None:
    with patch("keyring.get_keyring", return_value=object.__new__(FailKeyring)):
        storage = get_default_storage()
    assert isinstance(storage, FileTokenStorage)


def test_get_default_storage_returns_keyring_when_available(tmp_path: Path) -> None:
    with (
        patch("keyring.get_keyring", return_value=MagicMock(spec=object)),
        patch("keyring.get_password", return_value=None),
    ):
        storage = get_default_storage(token_path=tmp_path / "tokens.json")
    assert isinstance(storage, KeyringTokenStorage)


def test_get_default_storage_uses_custom_fallback_path(tmp_path: Path) -> None:
    custom_path = tmp_path / "custom.json"
    with patch("keyring.get_keyring", return_value=object.__new__(FailKeyring)):
        storage = get_default_storage(token_path=custom_path)
    assert isinstance(storage, FileTokenStorage)


def test_get_default_storage_falls_back_to_file_when_keyring_broken_at_runtime(
    tmp_path: Path,
) -> None:
    """A backend that isn't FailKeyring can still blow up on the first real
    call (e.g. a broken D-Bus Secret Service) — probe it and fall back."""
    with (
        patch("keyring.get_keyring", return_value=MagicMock(spec=object)),
        patch("keyring.get_password", side_effect=RuntimeError("DBus broken")),
    ):
        storage = get_default_storage(token_path=tmp_path / "tokens.json")
    assert isinstance(storage, FileTokenStorage)

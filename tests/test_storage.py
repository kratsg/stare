"""Tests for stare.storage."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import keyring.errors
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

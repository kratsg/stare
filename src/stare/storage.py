"""Token storage backends for stare."""

from __future__ import annotations

import contextlib
import os
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

import keyring
import keyring.errors
from keyring.backends.fail import Keyring as FailKeyring
from platformdirs import user_data_dir

from stare.models.auth import _StoredToken

_DEFAULT_TOKEN_PATH = Path(user_data_dir("stare")) / "tokens.json"


class TokenStorage(ABC):
    """Abstract base class for token storage backends."""

    @abstractmethod
    def load(self) -> _StoredToken | None:
        """Return stored tokens, or None if absent."""

    @abstractmethod
    def save(self, token: _StoredToken) -> None:
        """Persist tokens to storage."""

    @abstractmethod
    def delete(self) -> None:
        """Delete stored tokens; no-op if absent."""

    @abstractmethod
    def exists(self) -> bool:
        """Return True if tokens are currently stored."""

    @property
    @abstractmethod
    def lock_path(self) -> Path:
        """Path to the lock file for this storage backend."""


class FileTokenStorage(TokenStorage):
    """Stores tokens as a JSON file on disk."""

    def __init__(self, token_path: Path) -> None:
        """Store the path where the token JSON file will be read and written."""
        self._path = token_path

    def load(self) -> _StoredToken | None:
        """Return stored tokens, or None if the file does not exist."""
        if not self._path.exists():
            return None
        return _StoredToken.model_validate_json(self._path.read_text(encoding="utf-8"))

    def save(self, token: _StoredToken) -> None:
        """Write tokens to the JSON file, creating parent directories as needed.

        Written atomically to a 0o600 temp file in the same directory, then
        renamed onto the target, so the file is never briefly world-readable
        or observable mid-write.
        """
        self._path.parent.mkdir(parents=True, exist_ok=True)
        # mkstemp creates the file with mode 0o600 up front (no chmod race).
        fd, tmp_name = tempfile.mkstemp(
            dir=self._path.parent, prefix=f".{self._path.name}.", suffix=".tmp"
        )
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(token.model_dump_json())
            tmp_path.replace(self._path)
        except BaseException:
            tmp_path.unlink(missing_ok=True)
            raise

    def delete(self) -> None:
        """Delete the token file; no-op if it does not exist."""
        if self._path.exists():
            self._path.unlink()

    def exists(self) -> bool:
        """Return True if the token file exists."""
        return self._path.exists()

    @property
    def lock_path(self) -> Path:
        """Return the path to the advisory lock file for this storage backend."""
        return self._path.with_suffix(".lock")


class KeyringTokenStorage(TokenStorage):
    """Stores tokens as a JSON blob in the OS-native credential store.

    Uses macOS Keychain, Linux Secret Service, or Windows Credential Locker
    depending on the platform.  The entire :class:`_StoredToken` is persisted
    as a single JSON string to avoid partial-write races.
    """

    SERVICE_NAME = "stare"
    ENTRY_KEY = "tokens"

    def load(self) -> _StoredToken | None:
        """Return stored tokens from the keyring, or None if absent."""
        data = keyring.get_password(self.SERVICE_NAME, self.ENTRY_KEY)
        if data is None:
            return None
        return _StoredToken.model_validate_json(data)

    def save(self, token: _StoredToken) -> None:
        """Persist tokens as a JSON blob in the OS-native credential store."""
        keyring.set_password(self.SERVICE_NAME, self.ENTRY_KEY, token.model_dump_json())

    def delete(self) -> None:
        """Delete the keyring entry; no-op if it does not exist."""
        with contextlib.suppress(keyring.errors.PasswordDeleteError):
            keyring.delete_password(self.SERVICE_NAME, self.ENTRY_KEY)

    def exists(self) -> bool:
        """Return True if a token entry exists in the keyring."""
        return keyring.get_password(self.SERVICE_NAME, self.ENTRY_KEY) is not None

    @property
    def lock_path(self) -> Path:
        """Return the path to the advisory lock file for this storage backend."""
        return Path(user_data_dir("stare")) / "tokens.lock"

    def migrate_from_file(self, file_path: Path) -> None:
        """One-time migration from plaintext file to keyring. Idempotent."""
        if self.exists():
            return
        file_storage = FileTokenStorage(file_path)
        token = file_storage.load()
        if token is None:
            return
        self.save(token)
        file_storage.delete()


def get_default_storage(token_path: Path | None = None) -> TokenStorage:
    """Return the best available storage backend.

    Uses :class:`KeyringTokenStorage` when the OS keyring is functional, and
    performs a one-time migration from the plaintext file if needed.  Falls
    back to :class:`FileTokenStorage` when no keyring backend is registered
    (headless servers, CI environments) or when a registered backend raises
    on first use — e.g. a Secret Service that's present but broken at the
    D-Bus protocol level, which surfaces as unwrapped, backend-specific
    exceptions that neither ``secretstorage`` nor ``keyring`` normalize.
    """
    file_path = token_path or _DEFAULT_TOKEN_PATH
    backend = keyring.get_keyring()
    if isinstance(backend, FailKeyring):
        return FileTokenStorage(file_path)
    keyring_storage = KeyringTokenStorage()
    try:
        keyring_storage.migrate_from_file(file_path)
    except Exception:  # noqa: BLE001 - backend failures are unpredictable, see docstring
        return FileTokenStorage(file_path)
    return keyring_storage

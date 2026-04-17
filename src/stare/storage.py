"""Token storage backends for stare."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from stare.models.auth import _StoredToken


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
        self._path = token_path

    def load(self) -> _StoredToken | None:
        if not self._path.exists():
            return None
        return _StoredToken.model_validate_json(self._path.read_text())

    def save(self, token: _StoredToken) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(token.model_dump_json())

    def delete(self) -> None:
        if self._path.exists():
            self._path.unlink()

    def exists(self) -> bool:
        return self._path.exists()

    @property
    def lock_path(self) -> Path:
        return self._path.with_suffix(".lock")

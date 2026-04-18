"""API error response models (401, 403, 404)."""

from __future__ import annotations

from stare.models.common import _Base


class ApiErrorResponse(_Base):
    """A structured error response from the Glance API."""

    status: int | None = None
    title: str | None = None
    detail: str | None = None

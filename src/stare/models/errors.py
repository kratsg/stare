"""API error response models (401, 403, 404)."""

from __future__ import annotations

from pydantic import Field

from stare.models.common import _Base


class ApiErrorResponse(_Base):
    """A structured error response from the Glance API."""

    status: int | None = Field(default=None, alias="status")
    title: str | None = Field(default=None, alias="title")
    detail: str | None = Field(default=None, alias="detail")

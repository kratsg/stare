"""Search and list result models."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import AliasChoices, Field

from stare.models.analysis import Analysis
from stare.models.common import _Base
from stare.models.paper import Paper

T = TypeVar("T")


class _SearchResultsBase(_Base, Generic[T]):
    """Generic search result container shared by all search endpoints.

    The two live endpoints return different JSON keys for the total count
    (``totalRows`` from /searchAnalysis, ``numberOfResults`` from
    /searchPaper).  Both are accepted and stored under the same Python
    attribute ``total_rows``.
    """

    total_rows: int | None = Field(
        default=None,
        validation_alias=AliasChoices("totalRows", "numberOfResults"),
        serialization_alias="numberOfResults",
    )
    results: list[T] = Field(default_factory=list)


class AnalysisSearchResult(_SearchResultsBase[Analysis]):
    """Top-level response from GET /searchAnalysis."""


class PaperSearchResult(_SearchResultsBase[Paper]):
    """Top-level response from GET /searchPaper."""


class PublicationRef(_Base):
    """A minimal publication reference returned by /publications/search."""

    reference_code: str | None = Field(default=None, alias="referenceCode")
    type: str | None = Field(default=None, alias="type")


class TriggerCategory(_Base):
    """The category and year for a trigger."""

    name: str | None = Field(default=None, alias="name")
    year: str | None = Field(default=None, alias="year")


class Trigger(_Base):
    """A trigger entry returned by /triggers/search."""

    name: str | None = Field(default=None, alias="name")
    category: TriggerCategory | None = Field(default=None, alias="category")

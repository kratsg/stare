"""Search and list result models."""

from __future__ import annotations

from pydantic import Field

from stare.models.analysis import Analysis
from stare.models.common import _Base
from stare.models.paper import Paper


class SearchResult(_Base):
    """Top-level response from GET /searchAnalysis."""

    total_rows: int | None = Field(default=None, alias="totalRows")
    results: list[Analysis] = Field(default_factory=list, alias="results")


class PaperSearchResult(_Base):
    """Top-level response from GET /searchPaper.

    Note: ``numberOfResults`` is returned as a string by the API, not an integer.
    """

    number_of_results: str | None = Field(default=None, alias="numberOfResults")
    results: list[Paper] = Field(default_factory=list, alias="results")


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

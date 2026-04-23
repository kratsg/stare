"""Search and list result models."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import Field

from stare.models.analysis import Analysis
from stare.models.common import _Base
from stare.models.confnote import ConfNote
from stare.models.enums import LenientPublicationType
from stare.models.paper import Paper
from stare.models.pubnote import PubNote

T = TypeVar("T")


class _SearchResultsBase(_Base, Generic[T]):
    """Generic search result container shared by all search endpoints."""

    number_of_results: int = Field(default=0, alias="numberOfResults")
    results: list[T] = Field(default_factory=list)


class AnalysisSearchResult(_SearchResultsBase[Analysis]):
    """Top-level response from GET /searchAnalysis."""


class ConfNoteSearchResult(_SearchResultsBase[ConfNote]):
    """Top-level response from GET /searchConfnote."""


class PaperSearchResult(_SearchResultsBase[Paper]):
    """Top-level response from GET /searchPaper."""


class PubNoteSearchResult(_SearchResultsBase[PubNote]):
    """Top-level response from GET /searchPubnote."""


class PublicationRef(_Base):
    """A minimal publication reference returned by /publications/search."""

    reference_code: str | None = None
    type: LenientPublicationType | None = None


class TriggerCategory(_Base):
    """The category and year for a trigger."""

    name: str | None = None
    year: str | None = None


class Trigger(_Base):
    """A trigger entry returned by /triggers/search."""

    name: str | None = None
    category: TriggerCategory | None = None

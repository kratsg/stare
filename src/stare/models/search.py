"""Search and list result models."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import Field

from stare.models.analysis import Analysis
from stare.models.common import Groups, _Base
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


class PublicationSummary(_Base):
    """A summary record returned by GET /searchPublication."""

    reference_code: str | None = Field(default=None, alias="referenceCode")
    temporary_reference_code: str | None = Field(
        default=None, alias="temporaryReferenceCode"
    )
    final_reference_code: str | None = Field(default=None, alias="finalReferenceCode")
    type: LenientPublicationType | None = None
    status: str | None = None
    short_title: str | None = Field(default=None, alias="shortTitle")
    groups: Groups | None = None


class PublicationSearchResult(_SearchResultsBase[PublicationSummary]):
    """Top-level response from GET /searchPublication."""


class TriggerCategory(_Base):
    """The category of a trigger (from GET /searchTrigger)."""

    name: str | None = None


class Trigger(_Base):
    """A trigger entry returned by GET /searchTrigger."""

    name: str | None = None
    year: str | None = None
    category: TriggerCategory | None = None


class TriggerSearchResult(_SearchResultsBase[Trigger]):
    """Top-level response from GET /searchTrigger."""


class Leadgroup(_Base):
    """A leading physics group returned by GET /searchLeadgroup."""

    name: str | None = None


class LeadgroupSearchResult(_SearchResultsBase[Leadgroup]):
    """Top-level response from GET /searchLeadgroup."""


class Subgroup(_Base):
    """A physics subgroup returned by GET /searchSubgroup."""

    name: str | None = None


class SubgroupSearchResult(_SearchResultsBase[Subgroup]):
    """Top-level response from GET /searchSubgroup."""

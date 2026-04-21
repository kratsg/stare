"""PUB note resource models."""

from __future__ import annotations

from datetime import date

from pydantic import Field

from stare.models.common import (
    Documentation,
    Groups,
    Metadata,
    RelatedPublication,
    TeamMember,
    _Base,
)
from stare.models.enums import LenientPaperStatus, LenientPhase1State


class PubNoteReader(_Base):
    """A reader assigned to review a PUB note."""

    cern_ccid: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    is_first_reader: bool | None = None
    is_second_reader: bool | None = None


class PubNotePhase1(_Base):
    """Phase 1 lifecycle metadata for a PUB note."""

    state: LenientPhase1State | None = None
    start_date: date | None = None
    draft_cds_url: str | None = Field(default=None, alias="draftNoteCdsUrl")
    readers: list[PubNoteReader] = Field(default_factory=list)
    presentation_date: date | None = None
    group_approval_on: date | None = None
    first_reader_draft_sign_off: str | None = None
    date_of_atlas_circulation: date | None = None
    proceed_to_sign_off_on: date | None = None
    first_reader_sign_off: str | None = None
    second_reader_sign_off: str | None = None
    public_web_page_url: str | None = Field(
        default=None, alias="publicWebPageUrlForFiguresAndTables"
    )
    release_date: date | None = None


class PubNote(_Base):
    """An ATLAS PUB note."""

    temp_reference_code: str | None = Field(
        default=None, alias="temporaryReferenceCode"
    )
    status: LenientPaperStatus | None = None
    short_title: str | None = None
    public_short_title: str | None = None
    full_title: str | None = None
    groups: Groups | None = None
    documentation: Documentation | None = None
    analysis_team: list[TeamMember] = Field(default_factory=list)
    metadata: Metadata | None = None
    associated_analysis: RelatedPublication | None = None
    superseded_by: RelatedPublication | None = None
    phase1: PubNotePhase1 | None = None

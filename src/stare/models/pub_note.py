"""PUB note resource models."""

from __future__ import annotations

from pydantic import Field

from stare.models.common import (
    _Base,
    Documentation,
    Groups,
    Metadata,
    RelatedPublication,
    TeamMember,
)


class PubNoteReader(_Base):
    """A reader assigned to review a PUB note."""

    cern_ccid: str | None = Field(default=None, alias="cernCcid")
    first_name: str | None = Field(default=None, alias="firstName")
    last_name: str | None = Field(default=None, alias="lastName")
    email: str | None = Field(default=None, alias="email")
    is_first_reader: bool | None = Field(default=None, alias="isFirstReader")
    is_second_reader: bool | None = Field(default=None, alias="isSecondReader")


class PubNotePhase1(_Base):
    """Phase 1 lifecycle metadata for a PUB note."""

    state: str | None = Field(default=None, alias="state")
    start_date: str | None = Field(default=None, alias="startDate")
    draft_cds_url: str | None = Field(default=None, alias="draftNoteCdsUrl")
    readers: list[PubNoteReader] | None = Field(default=None, alias="readers")
    presentation_date: str | None = Field(default=None, alias="presentationDate")
    group_approval_on: str | None = Field(default=None, alias="groupApprovalOn")
    first_reader_draft_sign_off: str | None = Field(
        default=None, alias="firstReaderDraftSignOff"
    )
    date_of_atlas_circulation: str | None = Field(
        default=None, alias="dateOfAtlasCirculation"
    )
    proceed_to_sign_off_on: str | None = Field(
        default=None, alias="proceedToSignOffOn"
    )
    first_reader_sign_off: str | None = Field(
        default=None, alias="firstReaderSignOff"
    )
    second_reader_sign_off: str | None = Field(
        default=None, alias="secondReaderSignOff"
    )
    public_web_page_url: str | None = Field(
        default=None, alias="publicWebPageUrlForFiguresAndTables"
    )
    release_date: str | None = Field(default=None, alias="releaseDate")


class PubNote(_Base):
    """An ATLAS PUB note."""

    temp_reference_code: str | None = Field(
        default=None, alias="temporaryReferenceCode"
    )
    status: str | None = Field(default=None, alias="status")
    short_title: str | None = Field(default=None, alias="shortTitle")
    public_short_title: str | None = Field(default=None, alias="publicShortTitle")
    full_title: str | None = Field(default=None, alias="fullTitle")
    groups: Groups | None = Field(default=None, alias="groups")
    documentation: Documentation | None = Field(default=None, alias="documentation")
    analysis_team: list[TeamMember] | None = Field(
        default=None, alias="analysisTeam"
    )
    metadata: Metadata | None = Field(default=None, alias="metadata")
    associated_analysis: RelatedPublication | None = Field(
        default=None, alias="associatedAnalysis"
    )
    superseded_by: RelatedPublication | None = Field(
        default=None, alias="supersededBy"
    )
    phase1: PubNotePhase1 | None = Field(default=None, alias="phase1")

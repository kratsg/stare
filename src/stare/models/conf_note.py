"""CONF note resource models."""

from __future__ import annotations

from pydantic import Field

from stare.models.common import (
    Documentation,
    EditorialBoardMember,
    Groups,
    Metadata,
    RelatedPublication,
    TeamMember,
    _Base,
)


class _SignOffResponsible(_Base):
    cern_ccid: str | None = Field(default=None, alias="cernCcid")
    first_name: str | None = Field(default=None, alias="firstName")
    last_name: str | None = Field(default=None, alias="lastName")
    email: str | None = Field(default=None, alias="email")


class ConfNotePhase1(_Base):
    """Phase 1 lifecycle metadata for a CONF note."""

    state: str | None = Field(default=None, alias="state")
    start_date: str | None = Field(default=None, alias="startDate")
    cds_url: str | None = Field(default=None, alias="cdsDraftNoteUrl")
    editorial_board: list[EditorialBoardMember] | None = Field(
        default=None, alias="editorialBoard"
    )
    editorial_board_formed_on: str | None = Field(
        default=None, alias="editorialBoardFormedOn"
    )
    presentation_date: str | None = Field(default=None, alias="presentationDate")
    pgc_approved_analysis_on: str | None = Field(
        default=None, alias="principalGroupCoordinatorApprovedAnalysisOn"
    )
    eb_draft_sign_off: str | None = Field(
        default=None, alias="editorialBoardDraftSignOff"
    )
    first_sign_off_responsible: _SignOffResponsible | None = Field(
        default=None, alias="firstSignOffResponsible"
    )
    second_sign_off_responsible: _SignOffResponsible | None = Field(
        default=None, alias="secondSignOffResponsible"
    )
    first_sign_off: str | None = Field(default=None, alias="firstSignOff")
    second_sign_off: str | None = Field(default=None, alias="secondSignOff")
    public_web_page_url: str | None = Field(
        default=None, alias="publicWebPageUrlForFiguresAndTables"
    )
    release_date: str | None = Field(default=None, alias="releaseDate")


class ConfNote(_Base):
    """An ATLAS CONF note."""

    temp_reference_code: str | None = Field(
        default=None, alias="temporaryReferenceCode"
    )
    status: str | None = Field(default=None, alias="status")
    short_title: str | None = Field(default=None, alias="shortTitle")
    public_short_title: str | None = Field(default=None, alias="publicShortTitle")
    full_title: str | None = Field(default=None, alias="fullTitle")
    groups: Groups | None = Field(default=None, alias="groups")
    documentation: Documentation | None = Field(default=None, alias="documentation")
    analysis_team: list[TeamMember] | None = Field(default=None, alias="analysisTeam")
    metadata: Metadata | None = Field(default=None, alias="metadata")
    associated_analysis: RelatedPublication | None = Field(
        default=None, alias="associatedAnalysis"
    )
    superseded_by: RelatedPublication | None = Field(default=None, alias="supersededBy")
    phase1: ConfNotePhase1 | None = Field(default=None, alias="phase1")

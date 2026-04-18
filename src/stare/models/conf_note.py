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
    cern_ccid: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None


class ConfNotePhase1(_Base):
    """Phase 1 lifecycle metadata for a CONF note."""

    state: str | None = None
    start_date: str | None = None
    cds_url: str | None = Field(default=None, alias="cdsDraftNoteUrl")
    editorial_board: list[EditorialBoardMember] = Field(default_factory=list)
    editorial_board_formed_on: str | None = None
    presentation_date: str | None = None
    pgc_approved_analysis_on: str | None = Field(
        default=None, alias="principalGroupCoordinatorApprovedAnalysisOn"
    )
    eb_draft_sign_off: str | None = Field(
        default=None, alias="editorialBoardDraftSignOff"
    )
    first_sign_off_responsible: _SignOffResponsible | None = None
    second_sign_off_responsible: _SignOffResponsible | None = None
    first_sign_off: str | None = None
    second_sign_off: str | None = None
    public_web_page_url: str | None = Field(
        default=None, alias="publicWebPageUrlForFiguresAndTables"
    )
    release_date: str | None = None


class ConfNote(_Base):
    """An ATLAS CONF note."""

    temp_reference_code: str | None = Field(
        default=None, alias="temporaryReferenceCode"
    )
    status: str | None = None
    short_title: str | None = None
    public_short_title: str | None = None
    full_title: str | None = None
    groups: Groups | None = None
    documentation: Documentation | None = None
    analysis_team: list[TeamMember] = Field(default_factory=list)
    metadata: Metadata | None = None
    associated_analysis: RelatedPublication | None = None
    superseded_by: RelatedPublication | None = None
    phase1: ConfNotePhase1 | None = None

"""Analysis resource models."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from stare.models.common import (
    AmiGlanceLink,
    AnalysisContact,
    Documentation,
    EditorialBoardMember,
    Groups,
    Meeting,
    Metadata,
    RelatedPublication,
    TeamMember,
    _Base,
)


class AnalysisPhase0(_Base):
    """Phase 0 lifecycle metadata for an analysis."""

    state: str | None = Field(default=None, alias="state")
    start_date: str | None = Field(default=None, alias="startDate")
    main_physics_aim: str | None = Field(default=None, alias="mainPhysicsAim")
    dataset_used: str | None = Field(default=None, alias="datasetUsed")
    model_tested: str | None = Field(default=None, alias="modelTested")
    methods: str | None = Field(default=None, alias="methods")
    editorial_board_formed_on: str | None = Field(
        default=None, alias="editorialBoardFormedOn"
    )
    pgc_or_sgc_sign_off_date: str | None = Field(
        default=None, alias="pgcOrSgcSignOffDate"
    )
    analysis_contacts: list[AnalysisContact] | None = Field(
        default=None, alias="analysisContacts"
    )
    editorial_board: list[EditorialBoardMember] | None = Field(
        default=None, alias="editorialBoard"
    )
    eoi_meeting: list[Meeting] | None = Field(default=None, alias="eoiMeeting")
    editorial_board_request_meeting: list[Meeting] | None = Field(
        default=None, alias="editorialBoardRequestMeeting"
    )
    pre_approval_meeting: list[Meeting] | None = Field(
        default=None, alias="preApprovalMeeting"
    )
    approval_meeting: list[Meeting] | None = Field(
        default=None, alias="approvalMeeting"
    )


class Analysis(_Base):
    """A single ATLAS analysis record."""

    reference_code: str | None = Field(default=None, alias="referenceCode")
    creation_date: str | None = Field(default=None, alias="creationDate")
    status: str | None = Field(default=None, alias="status")
    short_title: str | None = Field(default=None, alias="shortTitle")
    public_short_title: str | None = Field(default=None, alias="publicShortTitle")
    groups: Groups | None = Field(default=None, alias="groups")
    ami_glance: list[AmiGlanceLink] | None = Field(default=None, alias="amiGlance")
    documentation: Documentation | None = Field(default=None, alias="documentation")
    analysis_team: list[TeamMember] | None = Field(default=None, alias="analysisTeam")
    metadata: Metadata | None = Field(default=None, alias="metadata")
    related_publications: list[RelatedPublication] | None = Field(
        default=None, alias="relatedPublications"
    )
    phase0: AnalysisPhase0 | None = Field(default=None, alias="phase0")
    extra_metadata: dict[str, Any] | None = Field(default=None, alias="extraMetadata")

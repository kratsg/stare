"""Analysis resource models."""

from __future__ import annotations

from datetime import datetime
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
from stare.models.enums import LenientAnalysisStatus, LenientPhaseState


class AnalysisPhase0(_Base):
    """Phase 0 lifecycle metadata for an analysis."""

    state: LenientPhaseState | None = None
    start_date: datetime | None = None
    main_physics_aim: str | None = None
    dataset_used: str | None = None
    model_tested: str | None = None
    methods: str | None = None
    editorial_board_formed_on: datetime | None = None
    pgc_or_sgc_sign_off_date: datetime | None = None
    analysis_contacts: list[AnalysisContact] = Field(default_factory=list)
    editorial_board: list[EditorialBoardMember] = Field(default_factory=list)
    eoi_meeting: list[Meeting] = Field(default_factory=list)
    editorial_board_request_meeting: list[Meeting] = Field(default_factory=list)
    pre_approval_meeting: list[Meeting] = Field(default_factory=list)
    approval_meeting: list[Meeting] = Field(default_factory=list)


class Analysis(_Base):
    """A single ATLAS analysis record."""

    reference_code: str | None = None
    creation_date: datetime | None = None
    status: LenientAnalysisStatus | None = None
    short_title: str | None = None
    public_short_title: str | None = None
    groups: Groups | None = None
    ami_glance: list[AmiGlanceLink] = Field(default_factory=list)
    documentation: Documentation | None = None
    analysis_team: list[TeamMember] = Field(default_factory=list)
    metadata: Metadata | None = None
    related_publications: list[RelatedPublication] = Field(default_factory=list)
    phase0: AnalysisPhase0 | None = None
    extra_metadata: dict[str, Any] | None = None

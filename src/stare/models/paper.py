"""Paper resource models (Phase1, Phase2, SubmissionPhase)."""

from __future__ import annotations

from datetime import date

from pydantic import AwareDatetime, Field, field_validator

from stare.models.common import (
    Documentation,
    EditorialBoardMember,
    Groups,
    Link,
    Metadata,
    Person,
    RelatedPublication,
    TeamMember,
    _Base,
)
from stare.models.enums import LenientPaperStatus, LenientPhaseState


class PaperPhase1(_Base):
    """Phase 1 of the paper lifecycle (review and approval)."""

    state: LenientPhaseState | None = None
    start_date: date | None = None
    editorial_board: list[EditorialBoardMember] = Field(default_factory=list)
    editorial_board_formed_on: date | None = None
    signed_off_by_language_editors_on: date | None = None
    presentation_date: date | None = None
    pgc_approved_analysis_on: date | None = Field(
        default=None, alias="principalGroupCoordinatorApprovedAnalysisOn"
    )
    eb_draft_sign_off: str | None = Field(
        default=None, alias="editorialBoardDraftSignOff"
    )
    draft_released_on: date | None = Field(default=None, alias="draftReleasedDate")
    pub_committee_chair: Person | None = Field(
        default=None, alias="publicationCommitteeChairDeputyOrDelegatedTo"
    )
    spokesperson: Person | None = Field(
        default=None, alias="spokespersonDeputyOrDelegatedTo"
    )
    atlas_meeting_date: date | None = None
    phase1_signed_off_by_pub_committee_on: date | None = Field(
        default=None, alias="phase1SignedOffByPublicationCommitteeChairOn"
    )


class PaperPhase2(_Base):
    """Phase 2 of the paper lifecycle (CERN review, revision, closure)."""

    state: LenientPhaseState | None = None
    start_date: date | None = None
    eb_draft2_sign_off_on: date | None = Field(
        default=None, alias="editorialBoardDraft2SignOffOn"
    )
    draft2_released_on: date | None = Field(default=None, alias="draft2ReleasedDate")
    sent_draft2_to_cern_on: date | None = None
    draft2_cern_sign_off_on: date | None = Field(
        default=None, alias="draft2CernSignOffDate"
    )
    paper_closure_meeting_urls: list[Link] = Field(default_factory=list)
    preliminary_plots_released: bool | None = Field(
        default=None, alias="preliminaryPlotsAndResultsReleased"
    )
    date_of_paper_closure: date | None = None
    revised_draft_signed_off_by_eb_chair_on: date | None = Field(
        default=None, alias="revisedDraftSignedOffByEditorialBoardChairOn"
    )
    pub_committee_chair_or_deputy: Person | None = Field(
        default=None, alias="publicationCommitteeChairOrDeputy"
    )
    revised_draft_signed_off_by_pub_committee_on: date | None = Field(
        default=None, alias="revisedDraftSignedOffByPublicationCommitteeChairOrDeputyOn"
    )
    revised_draft_signed_off_by_spokesperson_delegated_on: date | None = None
    revised_draft_signed_off_by_spokesperson_or_deputy_on: date | None = None


class SubmissionPhase(_Base):
    """Submission phase: arXiv, journal, final publication."""

    state: LenientPhaseState | None = None
    start_date: date | None = None
    arxiv_urls: list[Link] = Field(default_factory=list, alias="arXivUrls")
    final_title: str | None = Field(default=None, alias="finalTitleTex")
    final_submission_journal: str | None = None
    arxiv_submission_date: AwareDatetime | None = Field(
        default=None, alias="arXivSubmissionDate"
    )
    physics_briefings: list[Link] = Field(default_factory=list, alias="physicsBriefing")
    date_of_1st_referee_report: date | None = None
    journal_acceptance_date: date | None = None
    date_of_1st_proof: date | None = None
    final_journal_publications: list[Link] = Field(
        default_factory=list, alias="finalJournalPublication"
    )
    published_online_on: date | None = None

    @field_validator("arxiv_submission_date", mode="before")
    @classmethod
    def _parse_arxiv_date(cls, v: object) -> object:
        if isinstance(v, dict):
            date_str = v.get("date")
            time_str = v.get("time")
            if date_str and time_str:
                return f"{date_str}T{time_str}"
            return date_str
        return v


class Paper(_Base):
    """A published ATLAS paper."""

    reference_code: str | None = None
    status: LenientPaperStatus | None = None
    short_title: str | None = None
    public_short_title: str | None = None
    full_title: str | None = None
    groups: Groups | None = None
    documentation: Documentation | None = None
    analysis_team: list[TeamMember] = Field(default_factory=list)
    metadata: Metadata | None = None
    associated_analysis: RelatedPublication | None = None
    phase1: PaperPhase1 | None = None
    phase2: PaperPhase2 | None = None
    submission: SubmissionPhase | None = None

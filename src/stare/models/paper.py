"""Paper resource models (Phase1, Phase2, SubmissionPhase)."""

from __future__ import annotations

from pydantic import Field

from stare.models.common import (
    Documentation,
    EditorialBoardMember,
    Groups,
    Metadata,
    Person,
    RelatedPublication,
    TeamMember,
    _Base,
)


class _Link(_Base):
    """A labelled URL (used for arXiv, paper closure, final publication, etc.)."""

    label: str | None = None
    url: str | None = None


class _ArxivSubmissionDate(_Base):
    date: str | None = None
    time: str | None = None


class PaperPhase1(_Base):
    """Phase 1 of the paper lifecycle (review and approval)."""

    state: str | None = None
    start_date: str | None = None
    editorial_board: list[EditorialBoardMember] = Field(default_factory=list)
    editorial_board_formed_on: str | None = None
    signed_off_by_language_editors_on: str | None = None
    presentation_date: str | None = None
    pgc_approved_analysis_on: str | None = Field(
        default=None, alias="principalGroupCoordinatorApprovedAnalysisOn"
    )
    eb_draft_sign_off: str | None = Field(
        default=None, alias="editorialBoardDraftSignOff"
    )
    released_on: str | None = None
    pub_committee_chair: Person | None = Field(
        default=None, alias="publicationCommitteeChairDeputyOrDelegatedTo"
    )
    spokesperson: Person | None = Field(
        default=None, alias="spokespersonDeputyOrDelegatedTo"
    )
    atlas_meeting_date: str | None = None
    phase1_signed_off_by_pub_committee_on: str | None = Field(
        default=None, alias="phase1SignedOffByPublicationCommitteeChairOn"
    )


class PaperPhase2(_Base):
    """Phase 2 of the paper lifecycle (CERN review, revision, closure)."""

    state: str | None = None
    start_date: str | None = None
    eb_draft2_sign_off_on: str | None = Field(
        default=None, alias="editorialBoardDraft2SignOffOn"
    )
    released_on: str | None = None
    sent_draft2_to_cern_on: str | None = None
    signed_off_by_cern_on: str | None = None
    paper_closure_meeting_urls: list[_Link] = Field(default_factory=list)
    preliminary_plots_released: str | None = Field(
        default=None, alias="preliminaryPlotsAndResultsReleased"
    )
    date_of_paper_closure: str | None = None
    revised_draft_signed_off_by_eb_chair_on: str | None = Field(
        default=None, alias="revisedDraftSignedOffByEditorialBoardChairOn"
    )
    pub_committee_chair_or_deputy: Person | None = Field(
        default=None, alias="publicationCommitteeChairOrDeputy"
    )
    revised_draft_signed_off_by_pub_committee_on: str | None = Field(
        default=None, alias="revisedDraftSignedOffByPublicationCommitteeChairOrDeputyOn"
    )
    revised_draft_signed_off_by_spokesperson_delegated_on: str | None = None
    revised_draft_signed_off_by_spokesperson_or_deputy_on: str | None = None


class SubmissionPhase(_Base):
    """Submission phase: arXiv, journal, final publication."""

    state: str | None = None
    start_date: str | None = None
    arxiv_url: _Link | None = Field(default=None, alias="arXivUrl")
    final_title: str | None = Field(default=None, alias="finalTitleTex")
    final_submission_journal: str | None = None
    arxiv_submission_date: _ArxivSubmissionDate | None = Field(
        default=None, alias="arXivSubmissionDate"
    )
    physics_briefing: _Link | None = None
    date_of_1st_referee_report: str | None = None
    journal_acceptance_date: str | None = None
    date_of_1st_proof: str | None = None
    final_journal_publication: _Link | None = None
    published_online_on: str | None = None


class Paper(_Base):
    """A published ATLAS paper."""

    reference_code: str | None = None
    status: str | None = None
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
    submission_phase: SubmissionPhase | None = None

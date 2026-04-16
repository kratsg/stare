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

    label: str | None = Field(default=None, alias="label")
    url: str | None = Field(default=None, alias="url")


class _ArxivSubmissionDate(_Base):
    date: str | None = Field(default=None, alias="date")
    time: str | None = Field(default=None, alias="time")


class PaperPhase1(_Base):
    """Phase 1 of the paper lifecycle (review and approval)."""

    state: str | None = Field(default=None, alias="state")
    start_date: str | None = Field(default=None, alias="startDate")
    editorial_board: list[EditorialBoardMember] | None = Field(
        default=None, alias="editorialBoard"
    )
    editorial_board_formed_on: str | None = Field(
        default=None, alias="editorialBoardFormedOn"
    )
    signed_off_by_language_editors_on: str | None = Field(
        default=None, alias="signedOffByLanguageEditorsOn"
    )
    presentation_date: str | None = Field(default=None, alias="presentationDate")
    pgc_approved_analysis_on: str | None = Field(
        default=None, alias="principalGroupCoordinatorApprovedAnalysisOn"
    )
    eb_draft_sign_off: str | None = Field(
        default=None, alias="editorialBoardDraftSignOff"
    )
    released_on: str | None = Field(default=None, alias="releasedOn")
    pub_committee_chair: Person | None = Field(
        default=None, alias="publicationCommitteeChairDeputyOrDelegatedTo"
    )
    spokesperson: Person | None = Field(
        default=None, alias="spokespersonDeputyOrDelegatedTo"
    )
    atlas_meeting_date: str | None = Field(default=None, alias="atlasMeetingDate")
    phase1_signed_off_by_pub_committee_on: str | None = Field(
        default=None, alias="phase1SignedOffByPublicationCommitteeChairOn"
    )


class PaperPhase2(_Base):
    """Phase 2 of the paper lifecycle (CERN review, revision, closure)."""

    state: str | None = Field(default=None, alias="state")
    start_date: str | None = Field(default=None, alias="startDate")
    eb_draft2_sign_off_on: str | None = Field(
        default=None, alias="editorialBoardDraft2SignOffOn"
    )
    released_on: str | None = Field(default=None, alias="releasedOn")
    sent_draft2_to_cern_on: str | None = Field(default=None, alias="sentDraft2ToCernOn")
    signed_off_by_cern_on: str | None = Field(default=None, alias="signedOffByCernOn")
    paper_closure_meeting_urls: list[_Link] | None = Field(
        default=None, alias="paperClosureMeetingUrls"
    )
    preliminary_plots_released: str | None = Field(
        default=None, alias="preliminaryPlotsAndResultsReleased"
    )
    date_of_paper_closure: str | None = Field(default=None, alias="dateOfPaperClosure")
    revised_draft_signed_off_by_eb_chair_on: str | None = Field(
        default=None, alias="revisedDraftSignedOffByEditorialBoardChairOn"
    )
    pub_committee_chair_or_deputy: Person | None = Field(
        default=None, alias="publicationCommitteeChairOrDeputy"
    )
    revised_draft_signed_off_by_pub_committee_on: str | None = Field(
        default=None, alias="revisedDraftSignedOffByPublicationCommitteeChairOrDeputyOn"
    )
    revised_draft_signed_off_by_spokesperson_delegated_on: str | None = Field(
        default=None, alias="revisedDraftSignedOffBySpokespersonDelegatedOn"
    )
    revised_draft_signed_off_by_spokesperson_or_deputy_on: str | None = Field(
        default=None, alias="revisedDraftSignedOffBySpokespersonOrDeputyOn"
    )


class SubmissionPhase(_Base):
    """Submission phase: arXiv, journal, final publication."""

    state: str | None = Field(default=None, alias="state")
    start_date: str | None = Field(default=None, alias="startDate")
    arxiv_url: _Link | None = Field(default=None, alias="arXivUrl")
    final_title: str | None = Field(default=None, alias="finalTitleTex")
    final_submission_journal: str | None = Field(
        default=None, alias="finalSubmissionJournal"
    )
    arxiv_submission_date: _ArxivSubmissionDate | None = Field(
        default=None, alias="arXivSubmissionDate"
    )
    physics_briefing: _Link | None = Field(default=None, alias="physicsBriefing")
    date_of_1st_referee_report: str | None = Field(
        default=None, alias="dateOf1stRefereeReport"
    )
    journal_acceptance_date: str | None = Field(
        default=None, alias="journalAcceptanceDate"
    )
    date_of_1st_proof: str | None = Field(default=None, alias="dateOf1stProof")
    final_journal_publication: _Link | None = Field(
        default=None, alias="finalJournalPublication"
    )
    published_online_on: str | None = Field(default=None, alias="publishedOnlineOn")


class Paper(_Base):
    """A published ATLAS paper."""

    reference_code: str | None = Field(default=None, alias="referenceCode")
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
    phase1: PaperPhase1 | None = Field(default=None, alias="phase1")
    phase2: PaperPhase2 | None = Field(default=None, alias="phase2")
    submission_phase: SubmissionPhase | None = Field(
        default=None, alias="submissionPhase"
    )

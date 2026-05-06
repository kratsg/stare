"""Paper resource models (Phase1, Phase2, PublicationPhase)."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from pydantic import AwareDatetime, Field, field_validator
from rich.columns import Columns
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from stare.models.common import (
    AnalysisTeam,
    Documentation,
    EditorialBoard,
    Groups,
    Link,
    Metadata,
    Person,
    RelatedPublication,
    _Base,
)
from stare.models.enums import (
    LenientPaperPhase1State,
    LenientPaperPhase2State,
    LenientPaperSubmissionState,
    PaperStatus,
)
from stare.settings import StareSettings
from stare.urls import paper_url

if TYPE_CHECKING:
    from rich.console import RenderableType


class PaperPhase1(_Base):
    """Phase 1 of the paper lifecycle (review and approval)."""

    state: LenientPaperPhase1State | None = None
    start_date: date | None = None
    editorial_board: EditorialBoard = Field(default_factory=EditorialBoard)
    editorial_board_formed_date: date | None = None
    language_editors_sign_off_date: date | None = None
    presentation_date: date | None = None
    pgc_approval_date: date | None = None
    editorial_board_draft_sign_off_date: date | None = None
    draft_released_date: date | None = None
    pubcomm_chair_or_deputy_or_delegated: Person | None = None
    spokesperson_or_deputy_or_delegated: Person | None = None
    atlas_meeting_date: date | None = None
    pubcomm_sign_off_date: date | None = None


class PaperPhase2(_Base):
    """Phase 2 of the paper lifecycle (CERN review, revision, closure)."""

    state: LenientPaperPhase2State | None = None
    start_date: date | None = None
    editorial_board_draft2_sign_off_date: date | None = None
    draft2_released_date: date | None = None
    draft2_sent_to_cern_date: date | None = None
    draft2_cern_sign_off_date: date | None = None
    paper_closure_meeting: list[Link] = Field(default_factory=list)
    preliminary_plots_and_results_released: bool | None = None
    paper_closure_date: date | None = None
    editorial_board_revised_sign_off_date: date | None = None
    pubcomm_chair_or_deputy_or_delegated: Person | None = None
    pubcomm_chair_or_deputy_sign_off_date: date | None = None
    spokesperson_delegated_sign_off_date: date | None = None
    spokesperson_or_deputy_sign_off_date: date | None = None


class PublicationPhase(_Base):
    """Publication phase: arXiv, journal, final publication."""

    state: LenientPaperSubmissionState | None = None
    start_date: date | None = None
    arxiv_urls: list[Link] = Field(default_factory=list)
    final_title_tex: str | None = None
    final_submission_journal: str | None = None
    arxiv_submission_date: AwareDatetime | None = None
    physics_briefing: list[Link] = Field(default_factory=list)
    first_referee_report_date: date | None = None
    journal_acceptance_date: date | None = None
    first_proof_date: date | None = Field(default=None, alias="1stProofDate")
    final_journal_publication: list[Link] = Field(default_factory=list)
    published_online_date: date | None = None

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

    def __rich__(self) -> Panel | None:
        """Return a Rich Panel with publication details, or None if the phase has no renderable fields."""
        rows: list[tuple[str, RenderableType]] = []

        def _link_texts(links_field: list[Link]) -> Text:
            return Text(", ").join(
                Text.from_markup(f"[link={lnk.url}]{lnk.label or lnk.url}[/link]")
                if lnk.url
                else Text(lnk.label or "")
                for lnk in links_field
            )

        if self.arxiv_urls:
            rows.append(("arXiv", _link_texts(self.arxiv_urls)))

        if self.final_submission_journal:
            rows.append(("Journal", Text(self.final_submission_journal)))

        if self.arxiv_submission_date:
            rows.append(("Submitted", Text(str(self.arxiv_submission_date.date()))))  # pylint: disable=no-member

        if self.journal_acceptance_date:
            rows.append(("Accepted", Text(str(self.journal_acceptance_date))))

        if self.published_online_date:
            rows.append(("Published", Text(str(self.published_online_date))))

        if self.physics_briefing:
            rows.append(("Briefings", _link_texts(self.physics_briefing)))

        if self.final_journal_publication:
            rows.append(("Final", _link_texts(self.final_journal_publication)))

        if not rows:
            return None

        grid = Table.grid(padding=(0, 1))
        grid.add_column(style="bold cyan", justify="right")
        grid.add_column()
        for label, value in rows:
            grid.add_row(label, value)
        return Panel(grid, title="Publication Phase", expand=True)


class Paper(_Base):
    """A published ATLAS paper."""

    reference_code: str = Field(pattern=r"^[A-Z]+-\d{4}-\d{2}$")
    status: PaperStatus
    short_title: str | None = None
    public_short_title: str | None = None
    full_title: str | None = None
    groups: Groups | None = None
    documentation: Documentation | None = None
    analysis_team: AnalysisTeam = Field(default_factory=AnalysisTeam)
    metadata: Metadata | None = None
    rivet_routines_url: str | None = None
    associated_analysis: RelatedPublication | None = None
    phase1: PaperPhase1 | None = None
    phase2: PaperPhase2 | None = None
    publication_phase: PublicationPhase | None = None

    def __rich__(self) -> Panel:
        """Return a Rich Panel summarising the paper for terminal display."""
        sections: list[RenderableType] = []

        # --- Titles ---
        title_lines: list[RenderableType] = []

        if self.short_title:
            title_lines.append(Text(f"Title: {self.short_title}", style="bold"))

        if self.public_short_title:
            title_lines.append(Text(f"Public: {self.public_short_title}", style="dim"))

        if self.full_title:
            title_lines.append(Text(f"Full: {self.full_title}", style="italic"))

        if self.documentation and self.documentation.supporting_internal_documents:
            title_lines.extend(
                Text.from_markup(f"Support: [link={d.url}]{d.label or d.url}[/link]")
                for d in self.documentation.supporting_internal_documents
                if d.url
            )

        if self.metadata and self.metadata.keywords:
            kw = ", ".join(
                k.name for k in self.metadata.keywords if k.name and k.name != "None"
            )
            if kw:
                title_lines.append(Text(f"Keywords: {kw}", style="cyan"))

        sections.append(Group(*title_lines))

        # ================================
        # --- 3 COLUMN SUMMARY ---
        # ================================

        summary_cols: list[RenderableType] = []

        if self.metadata and self.metadata.collisions:
            summary_cols.append(self.metadata.collisions)

        if self.groups:
            summary_cols.append(self.groups)

        timeline = Table.grid(padding=(0, 1))
        timeline.add_column(style="bold cyan", justify="right")
        timeline.add_column()
        timeline_has_rows = False

        if self.phase1:
            p1 = self.phase1
            if p1.start_date:
                timeline.add_row("Start", str(p1.start_date))
                timeline_has_rows = True
            if p1.editorial_board_formed_date:
                timeline.add_row("EdBoard", str(p1.editorial_board_formed_date))
                timeline_has_rows = True
            if p1.presentation_date:
                timeline.add_row("Presentation", str(p1.presentation_date))
                timeline_has_rows = True
            if p1.draft_released_date:
                timeline.add_row("Draft 1", str(p1.draft_released_date))
                timeline_has_rows = True

        if self.phase2:
            p2 = self.phase2
            if p2.draft2_released_date:
                timeline.add_row("Draft 2", str(p2.draft2_released_date))
                timeline_has_rows = True
            if p2.paper_closure_date:
                timeline.add_row("Closure", str(p2.paper_closure_date))
                timeline_has_rows = True

        if self.publication_phase:
            pub = self.publication_phase
            if pub.arxiv_submission_date:  # pylint: disable=no-member
                timeline.add_row("arXiv", str(pub.arxiv_submission_date.date()))  # pylint: disable=no-member
                timeline_has_rows = True
            if pub.published_online_date:  # pylint: disable=no-member
                timeline.add_row("Published", str(pub.published_online_date))  # pylint: disable=no-member
                timeline_has_rows = True

        if timeline_has_rows:
            summary_cols.append(Panel(timeline, title="Timeline", expand=True))

        if summary_cols:
            sections.append(Columns(summary_cols, expand=True))

        # ================================
        # --- PEOPLE ---
        # ================================

        people_cols: list[RenderableType] = []

        if self.analysis_team:
            people_cols.append(self.analysis_team)

        if self.phase1 and self.phase1.editorial_board:
            people_cols.append(self.phase1.editorial_board)

        if people_cols:
            sections.append(Columns(people_cols, expand=True))

        # --- Publication Phase section ---
        if self.publication_phase:
            pub_panel = self.publication_phase.__rich__()  # pylint: disable=no-member
            if pub_panel is not None:
                sections.append(pub_panel)

        # --- Header ---
        settings = StareSettings()
        url = paper_url(self.reference_code, web_base=settings.web_base_url)

        header = Text.from_markup(
            f"[bold cyan][link={url}]{self.reference_code}[/link][/bold cyan]"
        )

        if self.status:
            header.append(f"\n{self.status}", style="yellow")

        return Panel(
            Group(*sections),
            title=header,
            expand=True,
            border_style="blue",
        )

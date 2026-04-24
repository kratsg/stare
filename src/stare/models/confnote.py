"""CONF note resource models."""

from __future__ import annotations

from datetime import date

from pydantic import Field
from rich.columns import Columns
from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from stare.models.common import (
    AnalysisTeam,
    Documentation,
    EditorialBoard,
    Groups,
    Metadata,
    RelatedPublication,
    _Base,
)
from stare.models.enums import ConfnoteStatus, LenientConfnotePhase1State
from stare.settings import StareSettings
from stare.urls import confnote_url


class _SignOffResponsible(_Base):
    cern_ccid: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None


class ConfNotePhase1(_Base):
    """Phase 1 lifecycle metadata for a CONF note."""

    state: LenientConfnotePhase1State | None = None
    start_date: date | None = None
    cds_url: str | None = Field(default=None, alias="cdsDraftNoteUrl")
    editorial_board: EditorialBoard = Field(default_factory=EditorialBoard)
    editorial_board_formed_on: date | None = None
    presentation_date: date | None = None
    pgc_approved_analysis_on: date | None = Field(
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
    release_date: date | None = None


class ConfNote(_Base):
    """An ATLAS CONF note."""

    temp_reference_code: str = Field(
        alias="temporaryReferenceCode", pattern=r"^CONF-[A-Z]{4}-\d{4}-\d{2}$"
    )
    final_reference_code: str | None = Field(default=None, alias="finalReferenceCode")
    status: ConfnoteStatus
    short_title: str | None = None
    public_short_title: str | None = None
    full_title: str | None = None
    groups: Groups | None = None
    documentation: Documentation | None = None
    analysis_team: AnalysisTeam = Field(default_factory=AnalysisTeam)
    metadata: Metadata | None = None
    associated_analysis: RelatedPublication | None = None
    superseded_by: RelatedPublication | None = None
    phase1: ConfNotePhase1 | None = None

    def __rich__(self) -> Panel:
        """Return a Rich Panel summarising the CONF note for terminal display."""
        sections: list[RenderableType] = []

        # --- Titles (explicit labels) ---
        title_lines: list[RenderableType] = []

        if self.short_title:
            title_lines.append(Text(f"Title: {self.short_title}", style="bold"))

        if self.public_short_title:
            title_lines.append(Text(f"Public: {self.public_short_title}", style="dim"))

        if self.full_title:
            title_lines.append(Text(f"Full: {self.full_title}", style="italic"))

        # --- Support docs (top, inline links) ---
        if self.documentation and self.documentation.supporting_internal_documents:
            title_lines.extend(
                Text.from_markup(f"Support: [link={d.url}]{d.label or d.url}[/link]")
                for d in self.documentation.supporting_internal_documents
                if d.url
            )

        # --- Keywords (inline, no panel) ---
        if self.metadata and self.metadata.keywords:
            kw = ", ".join(k for k in self.metadata.keywords if k != "None")
            if kw:
                title_lines.append(Text(f"Keywords: {kw}", style="cyan"))

        sections.append(Group(*title_lines))

        # ================================
        # --- 3 COLUMN SUMMARY PANEL ---
        # ================================

        summary_cols: list[RenderableType] = []

        if self.metadata and self.metadata.collisions:
            summary_cols.append(self.metadata.collisions)

        if self.groups:
            summary_cols.append(self.groups)

        if self.phase1:
            p1 = self.phase1
            timeline = Table.grid(padding=(0, 1))
            timeline.add_column(style="bold cyan", justify="right")
            timeline.add_column()

            if p1.start_date:
                timeline.add_row("Start", str(p1.start_date))
            if p1.editorial_board_formed_on:
                timeline.add_row("EdBoard", str(p1.editorial_board_formed_on))
            if p1.presentation_date:
                timeline.add_row("Presentation", str(p1.presentation_date))
            if p1.release_date:
                timeline.add_row("Release", str(p1.release_date))

            summary_cols.append(Panel(timeline, title="Timeline", expand=True))

        if summary_cols:
            sections.append(Columns(summary_cols, expand=True))

        # ================================
        # --- PEOPLE (side-by-side) ---
        # ================================

        people_cols: list[RenderableType] = []

        if self.analysis_team:
            people_cols.append(self.analysis_team)

        if self.phase1 and self.phase1.editorial_board:
            people_cols.append(self.phase1.editorial_board)

        if people_cols:
            sections.append(Columns(people_cols, expand=True))

        # --- Header ---
        settings = StareSettings()
        url = confnote_url(self.temp_reference_code, web_base=settings.web_base_url)

        header = Text.from_markup(
            f"[bold cyan][link={url}]{self.temp_reference_code}[/link][/bold cyan]"
        )

        if self.final_reference_code:
            header.append(f" ({self.final_reference_code})", style="bold")

        if self.status:
            header.append(f"\n{self.status}", style="yellow")

        return Panel(
            Group(*sections),
            title=header,
            expand=True,
            border_style="blue",
        )

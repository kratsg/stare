"""CONF note resource models."""

from __future__ import annotations

from datetime import date

from pydantic import Field
from rich.panel import Panel
from rich.table import Table

from stare.models.common import (
    Documentation,
    EditorialBoard,
    Groups,
    Metadata,
    Person,
    RelatedPublication,
    Team,
    _Base,
    _base_people_cols,
    _base_summary_cols,
    _build_header,
    _build_title_lines,
    _document_panel,
)
from stare.models.enums import LenientConfnotePhase1State, LenientConfnoteStatus
from stare.settings import get_settings
from stare.urls import confnote_url


class ConfNotePhase1(_Base):
    """Phase 1 lifecycle metadata for a CONF note."""

    state: LenientConfnotePhase1State | None = None
    start_date: date | None = None
    draft_cds_url: str | None = None
    editorial_board: EditorialBoard = Field(default_factory=EditorialBoard)
    editorial_board_formed_date: date | None = None
    presentation_date: date | None = None
    pgc_approval_date: date | None = None
    editorial_board_draft_sign_off_date: date | None = None
    first_sign_off_responsible: Person | None = None
    second_sign_off_responsible: Person | None = None
    first_sign_off_date: date | None = None
    second_sign_off_date: date | None = None
    public_web_page_url_for_figures_and_tables: str | None = None
    release_date: date | None = None


class ConfNote(_Base):
    """An ATLAS CONF note."""

    temp_reference_code: str = Field(
        alias="temporaryReferenceCode", pattern=r"^CONF-[A-Z]{4}-\d{4}-\d{2}$"
    )
    final_reference_code: str | None = None
    status: LenientConfnoteStatus
    short_title: str | None = None
    public_short_title: str | None = None
    full_title: str | None = None
    groups: Groups | None = None
    documentation: Documentation | None = None
    analysis_team: Team = Field(default_factory=Team)
    metadata: Metadata | None = None
    related_analysis: RelatedPublication | None = None
    superseded_by: list[RelatedPublication] = Field(default_factory=list)
    phase1: ConfNotePhase1 | None = None

    def __rich__(self) -> Panel:
        """Return a Rich Panel summarising the CONF note for terminal display."""
        # --- Titles (explicit labels) ---
        title_lines = _build_title_lines(
            short_title=self.short_title,
            public_short_title=self.public_short_title,
            full_title=self.full_title,
            documentation=self.documentation,
            keywords=self.metadata.keywords if self.metadata else None,
        )

        # ================================
        # --- 3 COLUMN SUMMARY PANEL ---
        # ================================

        summary_cols = _base_summary_cols(self.metadata, self.groups)

        if self.phase1:
            p1 = self.phase1
            timeline = Table.grid(padding=(0, 1))
            timeline.add_column(style="bold cyan", justify="right")
            timeline.add_column()

            if p1.start_date:
                timeline.add_row("Start", str(p1.start_date))
            if p1.editorial_board_formed_date:
                timeline.add_row("EdBoard", str(p1.editorial_board_formed_date))
            if p1.presentation_date:
                timeline.add_row("Presentation", str(p1.presentation_date))
            if p1.release_date:
                timeline.add_row("Release", str(p1.release_date))

            summary_cols.append(Panel(timeline, title="Timeline", expand=True))

        # ================================
        # --- PEOPLE (side-by-side) ---
        # ================================

        people_cols = _base_people_cols(self.analysis_team)

        if self.phase1 and self.phase1.editorial_board:
            people_cols.append(self.phase1.editorial_board)

        # --- Header ---
        settings = get_settings()
        url = confnote_url(self.temp_reference_code, web_base=settings.web_base_url)
        header = _build_header(
            self.temp_reference_code,
            url,
            self.status,
            secondary_code=self.final_reference_code,
        )

        return _document_panel(title_lines, summary_cols, people_cols, header)

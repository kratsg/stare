"""Plot resource models."""

from __future__ import annotations

from datetime import date

from pydantic import Field
from rich.panel import Panel
from rich.table import Table

from stare.models.common import (
    Documentation,
    Groups,
    Metadata,
    RelatedPublication,
    Team,
    _Base,
    _base_people_cols,
    _base_summary_cols,
    _build_header,
    _build_title_lines,
    _document_panel,
)
from stare.models.enums import LenientPlotPhase1State, LenientPlotStatus
from stare.settings import StareSettings
from stare.urls import plot_url


class PlotPhase1(_Base):
    """Phase 1 lifecycle metadata for a plot."""

    state: LenientPlotPhase1State | None = None
    start_date: date | None = None
    draft_cds_url: str | None = None
    group_coordinator_sign_off: str | None = None
    final_cds_report: str | None = None


class Plot(_Base):
    """An ATLAS approval plot."""

    reference_code: str | None = None
    status: LenientPlotStatus | None = None
    short_title: str | None = None
    full_title: str | None = None
    groups: Groups | None = None
    documentation: Documentation | None = None
    analysis_team: Team = Field(default_factory=Team)
    metadata: Metadata | None = None
    superseded_by: list[RelatedPublication] = Field(default_factory=list)
    phase1: PlotPhase1 | None = None

    def __rich__(self) -> Panel:
        """Return a Rich Panel summarising the plot for terminal display."""
        # --- Titles (explicit labels) ---
        title_lines = _build_title_lines(
            short_title=self.short_title,
            full_title=self.full_title,
            documentation=self.documentation,
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
            timeline_has_rows = False

            if p1.start_date:
                timeline.add_row("Start", str(p1.start_date))
                timeline_has_rows = True
            if p1.group_coordinator_sign_off:
                timeline.add_row("Coord Sign-off", p1.group_coordinator_sign_off)
                timeline_has_rows = True
            if p1.final_cds_report:
                timeline.add_row("Final CDS Report", p1.final_cds_report)
                timeline_has_rows = True

            if timeline_has_rows:
                summary_cols.append(Panel(timeline, title="Timeline", expand=True))

        # ================================
        # --- PEOPLE ---
        # ================================

        people_cols = _base_people_cols(self.analysis_team)

        # --- Header ---
        settings = StareSettings()
        url = (
            plot_url(self.reference_code, web_base=settings.web_base_url)
            if self.reference_code
            else None
        )
        header = _build_header(
            self.reference_code or "(no reference code)", url, self.status
        )

        return _document_panel(title_lines, summary_cols, people_cols, header)

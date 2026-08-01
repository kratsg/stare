"""Plot resource models."""

from __future__ import annotations

from datetime import date

from pydantic import Field
from rich.columns import Columns
from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from stare.models.common import (
    Documentation,
    Groups,
    Metadata,
    RelatedPublication,
    Team,
    _Base,
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
        sections: list[RenderableType] = []

        # --- Titles (explicit labels) ---
        title_lines: list[RenderableType] = []

        if self.short_title:
            title_lines.append(Text(f"Title: {self.short_title}", style="bold"))

        if self.full_title:
            title_lines.append(Text(f"Full: {self.full_title}", style="italic"))

        # --- Support docs (top, inline links) ---
        if self.documentation and self.documentation.supporting_internal_documents:
            title_lines.extend(
                Text.from_markup(f"Support: [link={d.url}]{d.label or d.url}[/link]")
                for d in self.documentation.supporting_internal_documents
                if d.url
            )

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

        if summary_cols:
            sections.append(Columns(summary_cols, expand=True))

        # ================================
        # --- PEOPLE ---
        # ================================

        people_cols: list[RenderableType] = []

        if self.analysis_team:
            people_cols.append(self.analysis_team)

        if people_cols:
            sections.append(Columns(people_cols, expand=True))

        # --- Header ---
        settings = StareSettings()
        if self.reference_code:
            url = plot_url(self.reference_code, web_base=settings.web_base_url)
            header = Text.from_markup(
                f"[bold cyan][link={url}]{self.reference_code}[/link][/bold cyan]"
            )
        else:
            header = Text("(no reference code)", style="bold cyan")

        if self.status:
            header.append(f"\n{self.status}", style="yellow")

        return Panel(
            Group(*sections),
            title=header,
            expand=True,
            border_style="blue",
        )

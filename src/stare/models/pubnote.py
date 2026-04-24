"""PUB note resource models."""

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
    Groups,
    Metadata,
    RelatedPublication,
    _Base,
    _ListRootModel,
)
from stare.models.enums import ConfnoteStatus, LenientConfnotePhase1State
from stare.settings import StareSettings
from stare.urls import pubnote_url


class PubNoteReader(_Base):
    """A reader assigned to review a PUB note."""

    cern_ccid: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    is_first_reader: bool | None = None
    is_second_reader: bool | None = None


class Readers(_ListRootModel[PubNoteReader]):
    """Ordered list of PUB note readers, rendered as a titled panel."""

    def __rich__(self) -> Panel:
        """Return a Rich Panel listing all readers with their assigned role."""
        table = Table(show_header=False, expand=True)
        table.add_column()
        table.add_column(justify="right")
        for r in self:
            name = f"{r.first_name} {r.last_name}"
            if r.is_first_reader:
                role = "1st"
            elif r.is_second_reader:
                role = "2nd"
            else:
                role = ""
            table.add_row(name, role)
        return Panel(table, title="Readers")


class PubNotePhase1(_Base):
    """Phase 1 lifecycle metadata for a PUB note."""

    state: LenientConfnotePhase1State | None = None
    start_date: date | None = None
    draft_cds_url: str | None = Field(default=None, alias="draftNoteCdsUrl")
    readers: Readers = Field(default_factory=Readers)
    presentation_date: date | None = None
    group_approval_on: date | None = None
    first_reader_draft_sign_off: str | None = None
    date_of_atlas_circulation: date | None = None
    proceed_to_sign_off_on: date | None = None
    first_reader_sign_off: str | None = None
    second_reader_sign_off: str | None = None
    public_web_page_url: str | None = Field(
        default=None, alias="publicWebPageUrlForFiguresAndTables"
    )
    release_date: date | None = None


class PubNote(_Base):
    """An ATLAS PUB note."""

    temp_reference_code: str = Field(alias="temporaryReferenceCode")
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
    phase1: PubNotePhase1 | None = None

    def __rich__(self) -> Panel:
        """Return a Rich Panel summarising the PUB note for terminal display."""
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
            kw = ", ".join(k for k in self.metadata.keywords if k != "None")
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

        if self.phase1:
            p1 = self.phase1
            timeline = Table.grid(padding=(0, 1))
            timeline.add_column(style="bold cyan", justify="right")
            timeline.add_column()
            timeline_has_rows = False

            if p1.start_date:
                timeline.add_row("Start", str(p1.start_date))
                timeline_has_rows = True
            if p1.presentation_date:
                timeline.add_row("Presentation", str(p1.presentation_date))
                timeline_has_rows = True
            if p1.group_approval_on:
                timeline.add_row("Group Appr", str(p1.group_approval_on))
                timeline_has_rows = True
            if p1.release_date:
                timeline.add_row("Release", str(p1.release_date))
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

        if self.phase1 and self.phase1.readers:
            people_cols.append(self.phase1.readers)

        if people_cols:
            sections.append(Columns(people_cols, expand=True))

        # --- Header ---
        settings = StareSettings()
        url = pubnote_url(self.temp_reference_code, web_base=settings.web_base_url)

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

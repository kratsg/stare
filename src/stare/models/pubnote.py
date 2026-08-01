"""PUB note resource models."""

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
    _ListRootModel,
)
from stare.models.enums import LenientPubnotePhase1State, LenientPubnoteStatus
from stare.settings import get_settings
from stare.urls import pubnote_url


class PubNoteReader(_Base):
    """A reader assigned to review a PUB note."""

    cern_ccid: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    is_first_reader: bool
    is_second_reader: bool


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

    state: LenientPubnotePhase1State | None = None
    start_date: date | None = None
    draft_cds_url: str | None = None
    readers: Readers = Field(default_factory=Readers)
    presentation_date: date | None = None
    group_approval_date: date | None = None
    first_reader_draft_sign_off_date: date | None = None
    atlas_circulation_date: date | None = None
    proceed_to_sign_off_date: date | None = None
    first_reader_sign_off_date: date | None = None
    second_reader_sign_off_date: date | None = None
    public_web_page_url_for_figures_and_tables: str | None = None
    release_date: date | None = None


class PubNote(_Base):
    """An ATLAS PUB note."""

    temp_reference_code: str = Field(
        alias="temporaryReferenceCode", pattern=r"^PUB-[A-Z]{4}-\d{4}-\d{2}$"
    )
    final_reference_code: str | None = None
    status: LenientPubnoteStatus | None = None
    short_title: str | None = None
    public_short_title: str | None = None
    full_title: str | None = None
    groups: Groups | None = None
    documentation: Documentation | None = None
    analysis_team: Team = Field(default_factory=Team)
    metadata: Metadata | None = None
    related_analysis: RelatedPublication | None = None
    superseded_by: list[RelatedPublication] = Field(default_factory=list)
    phase1: PubNotePhase1 | None = None

    def __rich__(self) -> Panel:
        """Return a Rich Panel summarising the PUB note for terminal display."""
        # --- Titles ---
        title_lines = _build_title_lines(
            short_title=self.short_title,
            public_short_title=self.public_short_title,
            full_title=self.full_title,
            documentation=self.documentation,
            keywords=self.metadata.keywords if self.metadata else None,
        )

        # ================================
        # --- 3 COLUMN SUMMARY ---
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
            if p1.presentation_date:
                timeline.add_row("Presentation", str(p1.presentation_date))
                timeline_has_rows = True
            if p1.group_approval_date:
                timeline.add_row("Group Appr", str(p1.group_approval_date))
                timeline_has_rows = True
            if p1.release_date:
                timeline.add_row("Release", str(p1.release_date))
                timeline_has_rows = True

            if timeline_has_rows:
                summary_cols.append(Panel(timeline, title="Timeline", expand=True))

        # ================================
        # --- PEOPLE ---
        # ================================

        people_cols = _base_people_cols(self.analysis_team)

        if self.phase1 and self.phase1.readers:
            people_cols.append(self.phase1.readers)

        # --- Header ---
        settings = get_settings()
        url = pubnote_url(self.temp_reference_code, web_base=settings.web_base_url)
        header = _build_header(
            self.temp_reference_code,
            url,
            self.status,
            secondary_code=self.final_reference_code,
        )

        return _document_panel(title_lines, summary_cols, people_cols, header)

"""CONF note resource models."""

from __future__ import annotations

from datetime import date

from pydantic import Field
from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from stare.models.common import (
    Documentation,
    EditorialBoardMember,
    Groups,
    Metadata,
    RelatedPublication,
    TeamMember,
    _Base,
)
from stare.models.enums import LenientConfnotePhase1State, LenientConfnoteStatus
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
    editorial_board: list[EditorialBoardMember] = Field(default_factory=list)
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
    status: LenientConfnoteStatus
    short_title: str | None = None
    public_short_title: str | None = None
    full_title: str | None = None
    groups: Groups | None = None
    documentation: Documentation | None = None
    analysis_team: list[TeamMember] = Field(default_factory=list)
    metadata: Metadata | None = None
    associated_analysis: RelatedPublication | None = None
    superseded_by: RelatedPublication | None = None
    phase1: ConfNotePhase1 | None = None

    def __rich__(self) -> Panel:
        sections: list[RenderableType] = []

        # --- Titles ---
        if self.short_title or self.public_short_title:
            title_block = []
            if self.short_title:
                title_block.append(Text(self.short_title, style="bold"))
            if self.public_short_title:
                title_block.append(Text(self.public_short_title, style="dim"))
            sections.append(Group(*title_block))

        if self.full_title:
            sections.append(Text(self.full_title, style="italic"))

        # --- Physics (2-column table) ---
        if self.metadata and self.metadata.collisions:
            coll = self.metadata.collisions[0]
            physics = Table.grid(padding=(0, 2))
            physics.add_column(style="bold cyan", justify="right")
            physics.add_column()

            physics.add_row("Run", f"{coll.run} ({coll.year})")
            physics.add_row("√s", f"{coll.ecm_value} TeV")
            physics.add_row("Luminosity", f"{coll.luminosity_value} fb⁻¹")

            sections.append(Panel(physics, title="Physics", expand=False))

        # --- Groups (multi-column compact layout) ---
        if self.groups:
            group_table = Table.grid(expand=False)
            group_table.add_column(style="bold cyan", justify="right")
            group_table.add_column()

            if self.groups.leading_group:
                group_table.add_row("Leading", self.groups.leading_group)
            if self.groups.subgroups:
                group_table.add_row("Subgroups", ", ".join(self.groups.subgroups))
            if self.groups.other_groups:
                group_table.add_row("Other", ", ".join(self.groups.other_groups))

            sections.append(Panel(group_table, title="Groups", expand=False))

        # --- Keywords (wrap nicely) ---
        if self.metadata and self.metadata.keywords:
            kw = ", ".join(k for k in self.metadata.keywords if k != "None")
            sections.append(Panel(Text(kw), title="Keywords", expand=False))

        # --- Analysis team (table, highlight editors) ---
        if self.analysis_team:
            team_table = Table(show_header=True, header_style="bold magenta")
            team_table.add_column("Name")
            team_table.add_column("CCID", justify="right")

            for p in self.analysis_team:
                name = f"{p.first_name} {p.last_name}"
                if p.is_contact_editor:
                    name = f"[bold yellow]★ {name}[/bold yellow]"
                team_table.add_row(name, p.cern_ccid or "")

            sections.append(
                Panel(team_table, title=f"Analysis Team ({len(self.analysis_team)})")
            )

        # --- Phase1 / Timeline ---
        if self.phase1:
            p1 = self.phase1
            timeline = Table.grid(padding=(0, 2))
            timeline.add_column(style="bold cyan", justify="right")
            timeline.add_column()

            if p1.start_date:
                timeline.add_row("Start", str(p1.start_date))
            if p1.editorial_board_formed_on:
                timeline.add_row("EB formed", str(p1.editorial_board_formed_on))
            if p1.presentation_date:
                timeline.add_row("Presented", str(p1.presentation_date))
            if p1.release_date:
                timeline.add_row("Released", str(p1.release_date))

            sections.append(Panel(timeline, title="Timeline", expand=False))

        # --- Editorial board (simple list) ---
        if self.phase1 and self.phase1.editorial_board:
            names = [
                f"{p.first_name} {p.last_name}" for p in self.phase1.editorial_board
            ]
            sections.append(
                Panel("\n".join(names), title="Editorial Board", expand=False)
            )

        # --- Support docs ---
        if self.documentation and self.documentation.supporting_internal_documents:
            docs = Table.grid()
            docs.add_column(style="bold cyan")
            docs.add_column()

            for d in self.documentation.supporting_internal_documents:
                docs.add_row(d.label or "Doc", d.url or "")

            sections.append(Panel(docs, title="Support", expand=False))

        settings = StareSettings()
        url = confnote_url(self.temp_reference_code, web_base=settings.web_base_url)

        # --- Header ---
        header = Text()
        header.append_text(
            Text.from_markup(
                f"[link={url}]{self.temp_reference_code}[/link]", style="bold cyan"
            )
        )

        if self.final_reference_code:
            header.append_text(Text(f" ({self.final_reference_code})", style="bold"))

        header.append_text(Text(f"\n{self.status.value}", style="yellow"))

        return Panel(
            Group(*sections),
            title=header,
            expand=True,
            border_style="blue",
        )

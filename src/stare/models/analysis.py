"""Analysis resource models."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from pydantic import Field, SerializationInfo, model_serializer, model_validator
from rich.columns import Columns
from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from stare.models.common import (
    AmiGlanceLink,
    AnalysisContacts,
    AnalysisTeam,
    Documentation,
    EditorialBoard,
    Groups,
    Metadata,
    RelatedPublication,
    TypedMeeting,
    _Base,
)
from stare.models.enums import (
    AnalysisStatus,
    LenientAnalysisPhase0State,
    MeetingType,
)
from stare.settings import StareSettings
from stare.urls import analysis_url

_logger = logging.getLogger("stare")

# Maps API JSON keys to meeting type tags (and reverse).
_MEETING_API_KEYS: dict[str, str] = {
    MeetingType.EOI: "eoiMeeting",
    MeetingType.EDITORIAL_BOARD_REQUEST: "editorialBoardRequestMeeting",
    MeetingType.PRE_APPROVAL: "preApprovalMeeting",
    MeetingType.APPROVAL: "approvalMeeting",
}
_MEETING_API_KEY_TO_TYPE: dict[str, str] = {v: k for k, v in _MEETING_API_KEYS.items()}


class AnalysisPhase0(_Base):
    """Phase 0 lifecycle metadata for an analysis.

    The API sends four separate meeting lists (eoiMeeting, editorialBoardRequestMeeting,
    preApprovalMeeting, approvalMeeting). We flatten them into a single ``meetings``
    list and tag each entry with its role via ``TypedMeeting.meeting_type``.
    Serialization restores the original four keys for API round-trip fidelity.
    """

    state: LenientAnalysisPhase0State | None = None
    start_date: date | None = None
    main_physics_aim: str | None = None
    dataset_used: str | None = None
    model_tested: str | None = None
    methods: str | None = None
    editorial_board_formed_on: date | None = None
    pgc_or_sgc_sign_off_date: date | None = None
    analysis_contacts: AnalysisContacts = Field(default_factory=AnalysisContacts)
    editorial_board: EditorialBoard = Field(default_factory=EditorialBoard)
    meetings: list[TypedMeeting] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _flatten_meetings(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        meetings = list(data.get("meetings") or [])
        for api_key, meeting_type in _MEETING_API_KEY_TO_TYPE.items():
            for raw_m in data.pop(api_key, []) or []:
                tagged = (
                    {**raw_m, "meetingType": meeting_type}
                    if isinstance(raw_m, dict)
                    else raw_m
                )
                meetings.append(tagged)
        if meetings or "meetings" in data:
            data["meetings"] = meetings
        return data

    @model_serializer(mode="wrap")
    def _serialize(self, handler: Any, info: SerializationInfo) -> dict[str, Any]:
        result: dict[str, Any] = handler(self)
        raw_meetings = result.pop("meetings", [])
        mt_key = "meetingType" if info.by_alias else "meeting_type"
        groups: dict[str, list[dict[str, Any]]] = {
            api_key: [] for api_key in _MEETING_API_KEYS.values()
        }
        for m_dict in raw_meetings:
            mt_val = m_dict.pop(mt_key, None)
            try:
                mt = MeetingType(mt_val)
            except (ValueError, TypeError):
                continue
            api_key = _MEETING_API_KEYS.get(mt)
            if api_key:
                groups[api_key].append(m_dict)
        result.update(groups)
        return result


class Analysis(_Base):
    """A single ATLAS analysis record."""

    reference_code: str = Field(pattern=r"^ANA-[A-Z]+-\d{4}-\d{2}$")
    creation_date: date | None = None
    status: AnalysisStatus
    short_title: str | None = None
    public_short_title: str | None = None
    groups: Groups | None = None
    ami_glance: list[AmiGlanceLink] = Field(default_factory=list)
    documentation: Documentation | None = None
    analysis_team: AnalysisTeam = Field(default_factory=AnalysisTeam)
    metadata: Metadata | None = None
    related_publications: list[RelatedPublication] = Field(default_factory=list)
    phase0: AnalysisPhase0 | None = None
    extra_metadata: dict[str, Any] | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_extra_metadata(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        extra = data.get("extraMetadata")
        if extra is not None and not isinstance(extra, dict):
            ref = data.get("referenceCode", "<unknown>")
            _logger.warning(
                "extraMetadata for %r is not a dict (got %s) — coercing to {}",
                ref,
                type(extra).__name__,
            )
            data["extraMetadata"] = {}
        return data

    def __rich__(self) -> Panel:
        """Return a Rich Panel summarising the analysis for terminal display."""
        sections: list[RenderableType] = []

        # --- Titles ---
        title_lines: list[RenderableType] = []

        if self.short_title:
            title_lines.append(Text(f"Title: {self.short_title}", style="bold"))

        if self.public_short_title:
            title_lines.append(Text(f"Public: {self.public_short_title}", style="dim"))

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

        if self.phase0:
            p0 = self.phase0
            timeline = Table.grid(padding=(0, 1))
            timeline.add_column(style="bold cyan", justify="right")
            timeline.add_column()

            if p0.start_date:
                timeline.add_row("Start", str(p0.start_date))
            if p0.editorial_board_formed_on:
                timeline.add_row("EdBoard", str(p0.editorial_board_formed_on))
            if p0.pgc_or_sgc_sign_off_date:
                timeline.add_row("PGC/SGC", str(p0.pgc_or_sgc_sign_off_date))

            # Meeting rows — one per type, hyperlinked when a URL is available
            _meeting_labels = {
                MeetingType.EOI: "EOI",
                MeetingType.EDITORIAL_BOARD_REQUEST: "EB Req",
                MeetingType.PRE_APPROVAL: "Pre-appr",
                MeetingType.APPROVAL: "Approval",
            }
            for meeting_type, label in _meeting_labels.items():
                typed = [m for m in p0.meetings if m.meeting_type == meeting_type]
                if not typed:
                    continue
                latest = max(typed, key=lambda m: m.date or "")
                if latest.date:
                    date_str = latest.date.strftime("%Y-%m-%d")
                    if latest.link and latest.link.url:
                        cell = Text.from_markup(
                            f"[link={latest.link.url}]{date_str}[/link]"
                        )
                    else:
                        cell = Text(date_str)
                    timeline.add_row(label, cell)

            summary_cols.append(Panel(timeline, title="Timeline", expand=True))

        if summary_cols:
            sections.append(Columns(summary_cols, expand=True))

        # ================================
        # --- PEOPLE ---
        # ================================

        people_cols: list[RenderableType] = []

        if self.analysis_team:
            people_cols.append(self.analysis_team)

        if self.phase0 and self.phase0.editorial_board:
            people_cols.append(self.phase0.editorial_board)

        if self.phase0 and self.phase0.analysis_contacts:
            people_cols.append(self.phase0.analysis_contacts)

        if people_cols:
            sections.append(Columns(people_cols, expand=True))

        # --- Header ---
        settings = StareSettings()
        url = analysis_url(self.reference_code, web_base=settings.web_base_url)

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

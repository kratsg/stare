"""Analysis resource models."""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from pydantic import Field, SerializationInfo, model_serializer, model_validator
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from stare.models.common import (
    AmiGlanceLink,
    AnalysisFramework,
    AnalysisTeam,
    Dataset,
    Documentation,
    EditorialBoard,
    Groups,
    Metadata,
    RelatedPublication,
    Trigger,
    TypedMeeting,
    _Base,
    _base_people_cols,
    _base_summary_cols,
    _build_header,
    _build_title_lines,
    _document_panel,
)
from stare.models.enums import (
    LenientAnalysisPhase0State,
    LenientAnalysisStatus,
    MeetingType,
)
from stare.settings import get_settings
from stare.urls import analysis_url

_logger = logging.getLogger("stare")

# Maps API JSON keys to meeting type tags (and reverse).
_MEETING_API_KEYS: dict[str, str] = {
    MeetingType.EOI: "eoiMeetings",
    MeetingType.EDITORIAL_BOARD_REQUEST: "editorialBoardRequestMeetings",
    MeetingType.PRE_APPROVAL: "preApprovalMeetings",
    MeetingType.APPROVAL: "approvalMeetings",
}
_MEETING_API_KEY_TO_TYPE: dict[str, str] = {v: k for k, v in _MEETING_API_KEYS.items()}


class AnalysisMetadata(Metadata):
    """Additional physics and technical metadata for analyses."""

    triggers: list[Trigger] = Field(default_factory=list)
    analysis_framework: AnalysisFramework | None = None
    datasets: list[Dataset] = Field(default_factory=list)


class AnalysisPhase0(_Base):
    """Phase 0 lifecycle metadata for an analysis.

    The API sends four separate meeting lists (eoiMeetings, editorialBoardRequestMeetings,
    preApprovalMeetings, approvalMeetings). We flatten them into a single ``meetings``
    list and tag each entry with its role via ``TypedMeeting.meeting_type``.
    Serialization restores the original four keys for API round-trip fidelity.
    """

    state: LenientAnalysisPhase0State | None = None
    start_date: date | None = None
    main_physics_aim: str | None = None
    dataset_used: str | None = None
    model_tested: str | None = None
    methods: str | None = None
    editorial_board_formed_date: date | None = None
    pgc_or_sgc_sign_off_date: date | None = None
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
        unmapped: list[dict[str, Any]] = []
        for m_dict in raw_meetings:
            mt_val = m_dict.pop(mt_key, None)
            try:
                api_key = _MEETING_API_KEYS[MeetingType(mt_val)]
            except (ValueError, TypeError):
                # Unknown (lenient) meeting type — preserve instead of dropping.
                _logger.warning(
                    "Unknown meeting type %r — serializing under 'meetings'", mt_val
                )
                m_dict[mt_key] = mt_val
                unmapped.append(m_dict)
                continue
            groups[api_key].append(m_dict)
        result.update(groups)
        if unmapped:
            result["meetings"] = unmapped
        return result


class Analysis(_Base):
    """A single ATLAS analysis record."""

    reference_code: str = Field(pattern=r"^ANA-[A-Z]+-\d{4}-\d{2}$")
    creation_date: date | None = None
    status: LenientAnalysisStatus
    short_title: str | None = None
    public_short_title: str | None = None
    groups: Groups | None = None
    ami_glance: list[AmiGlanceLink] = Field(default_factory=list)
    documentation: Documentation | None = None
    analysis_team: AnalysisTeam = Field(default_factory=AnalysisTeam)
    metadata: AnalysisMetadata | None = None
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
        # --- Titles ---
        title_lines = _build_title_lines(
            short_title=self.short_title,
            public_short_title=self.public_short_title,
            documentation=self.documentation,
            keywords=self.metadata.keywords if self.metadata else None,
        )

        # ================================
        # --- 3 COLUMN SUMMARY ---
        # ================================

        summary_cols = _base_summary_cols(self.metadata, self.groups)

        if self.phase0:
            p0 = self.phase0
            timeline = Table.grid(padding=(0, 1))
            timeline.add_column(style="bold cyan", justify="right")
            timeline.add_column()
            timeline_has_rows = False

            if p0.start_date:
                timeline.add_row("Start", str(p0.start_date))
                timeline_has_rows = True
            if p0.editorial_board_formed_date:
                timeline.add_row("EdBoard", str(p0.editorial_board_formed_date))
                timeline_has_rows = True
            if p0.pgc_or_sgc_sign_off_date:
                timeline.add_row("PGC/SGC", str(p0.pgc_or_sgc_sign_off_date))
                timeline_has_rows = True

            # Meeting rows — one per type, hyperlinked when a URL is available
            _meeting_labels = {
                MeetingType.EOI: "EOI",
                MeetingType.EDITORIAL_BOARD_REQUEST: "EB Req",
                MeetingType.PRE_APPROVAL: "Pre-appr",
                MeetingType.APPROVAL: "Approval",
            }
            for meeting_type, label in _meeting_labels.items():
                dated: list[tuple[datetime, TypedMeeting]] = [
                    (m.date, m)
                    for m in p0.meetings
                    if m.meeting_type == meeting_type and m.date is not None
                ]
                if not dated:
                    continue
                meeting_date, latest = max(dated, key=lambda pair: pair[0])
                date_str = meeting_date.strftime("%Y-%m-%d")
                if latest.link and latest.link.url:
                    cell = Text.from_markup(
                        f"[link={latest.link.url}]{date_str}[/link]"
                    )
                else:
                    cell = Text(date_str)
                timeline.add_row(label, cell)
                timeline_has_rows = True

            if timeline_has_rows:
                summary_cols.append(Panel(timeline, title="Timeline", expand=True))

        # ================================
        # --- PEOPLE ---
        # ================================

        people_cols = _base_people_cols(self.analysis_team)

        if self.phase0 and self.phase0.editorial_board:
            people_cols.append(self.phase0.editorial_board)

        # --- Header ---
        settings = get_settings()
        url = analysis_url(self.reference_code, web_base=settings.web_base_url)
        header = _build_header(self.reference_code, url, self.status)

        return _document_panel(title_lines, summary_cols, people_cols, header)

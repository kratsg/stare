"""Analysis resource models."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from pydantic import Field, SerializationInfo, model_serializer, model_validator

from stare.models.common import (
    AmiGlanceLink,
    AnalysisContact,
    Documentation,
    EditorialBoardMember,
    Groups,
    Metadata,
    RelatedPublication,
    TeamMember,
    TypedMeeting,
    _Base,
)
from stare.models.enums import LenientAnalysisStatus, LenientPhaseState, MeetingType

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

    state: LenientPhaseState | None = None
    start_date: date | None = None
    main_physics_aim: str | None = None
    dataset_used: str | None = None
    model_tested: str | None = None
    methods: str | None = None
    editorial_board_formed_on: date | None = None
    pgc_or_sgc_sign_off_date: date | None = None
    analysis_contacts: list[AnalysisContact] = Field(default_factory=list)
    editorial_board: list[EditorialBoardMember] = Field(default_factory=list)
    meetings: list[TypedMeeting] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _flatten_meetings(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        meetings: list[dict[str, Any]] = []
        for api_key, meeting_type in _MEETING_API_KEY_TO_TYPE.items():
            for raw_m in data.pop(api_key, []) or []:
                tagged = (
                    {**raw_m, "meetingType": meeting_type}
                    if isinstance(raw_m, dict)
                    else raw_m
                )
                meetings.append(tagged)
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

    reference_code: str | None = None
    creation_date: date | None = None
    status: LenientAnalysisStatus | None = None
    short_title: str | None = None
    public_short_title: str | None = None
    groups: Groups | None = None
    ami_glance: list[AmiGlanceLink] = Field(default_factory=list)
    documentation: Documentation | None = None
    analysis_team: list[TeamMember] = Field(default_factory=list)
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

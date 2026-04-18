"""Semantic string enums for Glance API fields.

Each public enum documents the known value set for a field.
All enums are exposed in their "lenient" form via the ``Lenient*`` type
aliases, which accept unknown strings gracefully (logging a warning)
rather than raising a validation error.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Annotated

from pydantic import BeforeValidator

_logger = logging.getLogger("stare")


class StrEnum(str, Enum):
    """Python 3.10-compatible string enum base (StrEnum was added in 3.11)."""


def _lenient(enum_cls: type) -> Annotated:  # type: ignore[valid-type]
    """Return an Annotated validator that coerces str→enum or falls back to str."""

    def _validate(v: object) -> object:
        if not isinstance(v, str):
            return v
        try:
            return enum_cls(v)
        except ValueError:
            _logger.warning(
                "Unknown %s value %r — storing as raw string", enum_cls.__name__, v
            )
            return v

    return Annotated[enum_cls | str, BeforeValidator(_validate)]


class MeetingType(StrEnum):
    """Phase0 meeting role tags (used internally after flattening the 4 meeting lists)."""

    EOI = "eoi"
    EDITORIAL_BOARD_REQUEST = "editorial_board_request"
    PRE_APPROVAL = "pre_approval"
    APPROVAL = "approval"


class AnalysisStatus(StrEnum):
    """Observed status values for Analysis records."""

    ACTIVE = "Active"
    ANALYSIS_CLOSED = "Analysis Closed"
    PHASE0_ACTIVE = "Phase 0 Active"
    PHASE0_CLOSED = "Phase 0 Closed"


class PaperStatus(StrEnum):
    """Observed status values for Paper, ConfNote, and PubNote records."""

    SUBMISSION_CLOSED = "Submission Closed"
    ACTIVE = "Active"


class PhaseState(StrEnum):
    """Observed workflow state keys for phase0/phase1/phase2/submission phases."""

    # Human-readable states seen in test data
    ACTIVE = "Active"
    APPROVED = "Approved"
    FINISHED = "finished"
    # Internal workflow state identifiers seen in live API
    APPROVAL_ACCEPTANCE = "approval_acceptance"
    EDBOARD_MEETING = "edboard_meeting_data"
    EDBOARD_REQUEST_MEETING = "edboard_request_meeting_data"
    FIRST_ANALYSIS = "first_analysis_data"
    INTERNAL_NOTE = "internal_note_editors_definition"
    PAPER_SKIP = "paper_skip"
    PGC_SGC_SIGNOFF = "pgc_sgc_contact_signoff"
    PRE_APPROVAL_MEETING = "pre_approval_meeting_data"
    PUBLICATION_DRAFT = "publication_draft"
    SECOND_ANALYSIS = "second_analysis_data"


class CollisionType(StrEnum):
    """Observed collision type identifiers."""

    PP = "p-p"
    PBPB = "Pb-Pb"


class RepositoryType(StrEnum):
    """Observed repository type values."""

    ANALYSIS = "analysis"
    THESIS = "thesis"
    FRAMEWORK = "framework"


class PublicationType(StrEnum):
    """Observed publication type values (cross-references between record types)."""

    PAPER = "Paper"
    CONF_NOTE = "ConfNote"
    PUB_NOTE = "PubNote"
    ANALYSIS = "Analysis"


# Lenient type aliases — use these in model field annotations.
LenientAnalysisStatus = _lenient(AnalysisStatus)
LenientPaperStatus = _lenient(PaperStatus)
LenientPhaseState = _lenient(PhaseState)
LenientCollisionType = _lenient(CollisionType)
LenientRepositoryType = _lenient(RepositoryType)
LenientPublicationType = _lenient(PublicationType)

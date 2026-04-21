"""Semantic string enums for Glance API fields.

Each public enum documents the known value set for a field.
All enums are exposed in their "lenient" form via the ``Lenient*`` type
aliases, which accept unknown strings gracefully (logging a warning)
rather than raising a validation error.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Annotated, Any, TypeVar

from pydantic import BeforeValidator

_logger = logging.getLogger("stare")

_E = TypeVar("_E", bound="StrEnum")


class StrEnum(str, Enum):
    """Python 3.10-compatible string enum base (StrEnum was added in 3.11)."""


def _lenient(enum_cls: type[_E]) -> Any:
    """Return ``Annotated[EnumCls | str, BeforeValidator]`` for use in model fields.

    Unknown string values fall back to the raw string and log a warning.
    """

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

    CREATED = "Created"
    ANALYSIS_CLOSED = "Analysis Closed"
    PHASE0_ACTIVE = "Phase 0 Active"
    PHASE0_CLOSED = "Phase 0 Closed"


class PaperStatus(StrEnum):
    """Observed status values for Paper, ConfNote, and PubNote records."""

    NOT_STARTED = "Not Started"
    CLOSED = "Closed"
    PHASE1_ACTIVE = "Phase 1 Active"
    PHASE1_CLOSED = "Phase 1 Closed"
    PHASE2_ACTIVE = "Phase 2 Active"
    PHASE2_CLOSED = "Phase 2 Closed"
    SUBMISSION_ACTIVE = "Publication Phase Active"
    SUBMISSION_COMPLETED = "Completed"


class Phase0State(StrEnum):
    """Observed workflow state keys for phase0 phase."""

    NOT_STARTED = "Phase 0 Data"
    EOI_MEETING = "Expression of interest (EOI) meeting data"
    ANALYSIS_DEFINITION = "Analysis definition after EOI meeting"
    ANALYSIS_COORDINATORS_SELECTION = "Analysis contact and expert review selection"
    FIRST_ANALYSIS_DATA = "Analysis metadata"
    ANALYSIS_COORDINATORS_TIMELINE = "Analysis contacts' target date"
    SECOND_ANALYSIS_DATA = "Auxiliary metadata"
    INTERNAL_NOTE_EDITORS_DEFINITION = (
        "Internal note editors and contact editors appointment"
    )
    EDBOARD_REQUEST_MEETING_DATA = "Editorial Board request meeting and formation data"
    EDBOARD_MEETING_DATA = "Editorial Board meeting data"
    PRE_APPROVAL_MEETING_DATA = "Pre approval meeting data"
    PGC_SGC_CONTACT_SIGNOFF = "PGC or SGC pre approval sign-off"
    PUBLICATION_DRAFT = "Publication draft"
    APPROVAL_MEETING_DATA = "Approval meeting data"
    APPROVAL_ACCEPTANCE = "Approval acceptance"
    FINISHED = "Publications definition"
    PAPER_SKIP = "Skipped to Paper"
    CONF_SKIP = "Skipped to CONF Note"
    PUB_SKIP = "Skipped to PUB Note"
    CONF_CONTACT_EDITORS = "conf_contact_editors_definition"
    PUB_CONTACT_EDITORS = "pub_contact_editors_definition"
    PAPER_CONTACT_EDITORS = "paper_contact_editors_definition"


class Phase1State(StrEnum):
    """Observed workflow state keys for phase1 phase."""

    NOT_STARTED = "Phase 1 Data"
    STARTED = "Editorial Board"
    APPROVED_BY_REVIEWER = "Analysis Review"
    LGP_APPROVED = "Editorial Board Draft Sign-off"
    REVIEW_CLOSED = "Draft 1 Released to ATLAS"
    FINISHED = "Phase Closed"


class Phase2State(StrEnum):
    """Observed workflow state keys for phase2 phase."""

    STARTED = "Phase 2 Data"
    FINAL_REVIEW_CLOSED = "Draft 2 Approval Process"
    UPDATE_EDBOARD = "Revised Draft Final Sign-off by Editorial Board Chair"
    UPDATED_PUBCOMM = (
        "Revised Draft Final Sign-off by Publication Committee Chair or Deputy"
    )
    UPDATED_SPOKESPERSONDATE = "Final Sign-off by Spokesperson or Deputy"
    FINISHED = "Phase Closed"


class SubmissionState(StrEnum):
    """Observed workflow state keys for submission phase."""

    NOT_STARTED = "Publication Phase Launch"
    STARTED = "Tarball Receiving"
    TARBALL_RECEIVED = "CERN and ATLAS Collection"
    SUBMITTED_TO_ARXIV = "Journal Submission"
    SUBMITTED_TO_JOURNAL = "Journal Reports Receiving"
    JOURNAL_REPORT_RECEIVED = "Journal Reports Answering"
    JOURNAL_REPORT_ANSWERED = "Journal Acceptance"
    ACCEPTED_BY_JOURNAL = "Proofs Receiving"
    PROOFS_RECEIVED = "Proofs Answering"
    PROOF_ANSWERED = "Online Publication"
    PUBLISHED_ONLINE = "Final ArXiv Replacement"
    ERRATUM_REQUESTED = "Erratum Submission"
    ERRATUM_SUBMITTED = "Erratum Acceptance"
    FINAL_ARXIV_REPLACED = "Paper Finish"
    FINISHED = "Submission Closed"


class CollisionType(StrEnum):
    """Observed collision type identifiers."""

    PP = "p-p"
    P_PB = "p-Pb"
    PB_PB = "Pb-Pb"
    XE_XE = "Xe-Xe"
    COL_TYPE = "Col type"
    SEC_COL_TYPE = "Sec col type"
    TERT_COL_TYPE = "Tert col type"
    NE_NE = "NeNe"
    O_O = "OO"
    P_O = "pO"


class RepositoryType(StrEnum):
    """Observed repository type values."""

    CONF = "CONF"
    INT = "INT"
    PAP = "PAP"
    PUB = "PUB"


class PublicationType(StrEnum):
    """Observed publication type values (cross-references between record types)."""

    PAPER = "Paper"
    CONF_NOTE = "ConfNote"
    PUB_NOTE = "PubNote"
    ANALYSIS = "Analysis"


# Lenient type aliases — use these in model field annotations.
LenientMeetingType = _lenient(MeetingType)
LenientPhase0State = _lenient(Phase0State)
LenientPhase1State = _lenient(Phase1State)
LenientPhase2State = _lenient(Phase2State)
LenientSubmissionState = _lenient(SubmissionState)
LenientAnalysisStatus = _lenient(AnalysisStatus)
LenientPaperStatus = _lenient(PaperStatus)
LenientCollisionType = _lenient(CollisionType)
LenientRepositoryType = _lenient(RepositoryType)
LenientPublicationType = _lenient(PublicationType)

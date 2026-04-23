"""Tests for lenient StrEnum types used in stare models."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel

from stare.models.enums import (
    AnalysisPhase0State,
    AnalysisStatus,
    CollisionType,
    ConfnotePhase1State,
    ConfnoteStatus,
    LenientCollisionType,
    LenientConfnotePhase1State,
    LenientConfnoteStatus,
    LenientPublicationType,
    LenientRepositoryType,
    PaperPhase1State,
    PaperPhase2State,
    PaperStatus,
    PaperSubmissionState,
    PublicationType,
    RepositoryType,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _model(lenient_type: Any) -> Any:
    """Return a tiny pydantic model with a single `value` field of the given type."""

    class M(BaseModel):
        value: lenient_type | None = None

    return M


# ---------------------------------------------------------------------------
# AnalysisStatus
# ---------------------------------------------------------------------------


class TestAnalysisStatus:
    def test_known_values_parse(self) -> None:
        M = _model(AnalysisStatus)
        assert (
            M.model_validate({"value": "Analysis Closed"}).value
            == AnalysisStatus.ANALYSIS_CLOSED
        )
        assert (
            M.model_validate({"value": "Phase 0 Active"}).value
            == AnalysisStatus.PHASE0_ACTIVE
        )
        assert (
            M.model_validate({"value": "Phase 0 Closed"}).value
            == AnalysisStatus.PHASE0_CLOSED
        )
        assert M.model_validate({"value": "Created"}).value == AnalysisStatus.CREATED

    def test_enum_compares_equal_to_string(self) -> None:
        assert AnalysisStatus.CREATED.value == "Created"

    def test_round_trip(self) -> None:
        M = _model(AnalysisStatus)
        m = M.model_validate({"value": "Created"})
        dumped = m.model_dump()
        assert dumped["value"] == "Created"

    def test_none_default(self) -> None:
        M = _model(AnalysisStatus)
        assert M.model_validate({}).value is None


# ---------------------------------------------------------------------------
# PaperStatus
# ---------------------------------------------------------------------------


class TestPaperStatus:
    def test_known_values_parse(self) -> None:
        M = _model(PaperStatus)
        assert (
            M.model_validate({"value": "Completed"}).value
            == PaperStatus.SUBMISSION_CLOSED
        )


# ---------------------------------------------------------------------------
# ConfnoteStatus
# ---------------------------------------------------------------------------


class TestConfnoteStatus:
    def test_known_values_parse(self) -> None:
        M = _model(ConfnoteStatus)
        assert M.model_validate({"value": "Created"}).value == ConfnoteStatus.CREATED
        assert (
            M.model_validate({"value": "Phase 1 Active"}).value
            == ConfnoteStatus.PHASE1_ACTIVE
        )

    def test_unknown_falls_back(self, caplog) -> None:
        M = _model(LenientConfnoteStatus)
        with caplog.at_level(logging.WARNING, logger="stare"):
            result = M.model_validate({"value": "Unknown Confnote Status"})
        assert result.value == "Unknown Confnote Status"
        assert "ConfnoteStatus" in caplog.text


# ---------------------------------------------------------------------------
# PhaseState
# ---------------------------------------------------------------------------


class TestAnalysisPhase0State:
    def test_human_readable_states(self) -> None:
        M = _model(AnalysisPhase0State)
        assert (
            M.model_validate({"value": "Phase 0 Data"}).value
            == AnalysisPhase0State.NOT_STARTED
        )
        assert (
            M.model_validate({"value": "Publications definition"}).value
            == AnalysisPhase0State.FINISHED
        )

    def test_internal_workflow_states(self) -> None:
        M = _model(AnalysisPhase0State)
        assert (
            M.model_validate({"value": "Approval acceptance"}).value
            == AnalysisPhase0State.APPROVAL_ACCEPTANCE
        )
        assert (
            M.model_validate({"value": "Publication draft"}).value
            == AnalysisPhase0State.PUBLICATION_DRAFT
        )

    def test_live_api_workflow_states(self) -> None:
        M = _model(AnalysisPhase0State)
        assert (
            M.model_validate({"value": "Analysis definition after EOI meeting"}).value
            == AnalysisPhase0State.ANALYSIS_DEFINITION
        )
        assert (
            M.model_validate({"value": "Skipped to CONF Note"}).value
            == AnalysisPhase0State.CONF_SKIP
        )

    def test_additional_workflow_states(self) -> None:
        M = _model(AnalysisPhase0State)
        assert (
            M.model_validate(
                {"value": "Analysis contact and expert review selection"}
            ).value
            == AnalysisPhase0State.ANALYSIS_COORDINATORS_SELECTION
        )
        assert (
            M.model_validate({"value": "Analysis contacts' target date"}).value
            == AnalysisPhase0State.ANALYSIS_COORDINATORS_TIMELINE
        )
        assert (
            M.model_validate({"value": "Approval meeting data"}).value
            == AnalysisPhase0State.APPROVAL_MEETING_DATA
        )
        assert (
            M.model_validate(
                {"value": "Expression of interest (EOI) meeting data"}
            ).value
            == AnalysisPhase0State.EOI_MEETING
        )
        assert (
            M.model_validate({"value": "Skipped to PUB Note"}).value
            == AnalysisPhase0State.PUB_SKIP
        )


class TestPaperPhase1State:
    def test_human_readable_states(self) -> None:
        M = _model(PaperPhase1State)
        assert (
            M.model_validate({"value": "Phase 1 Data"}).value
            == PaperPhase1State.NOT_STARTED
        )
        assert (
            M.model_validate({"value": "Phase Closed"}).value
            == PaperPhase1State.FINISHED
        )

    def test_internal_workflow_states(self) -> None:
        M = _model(PaperPhase1State)
        assert (
            M.model_validate({"value": "Analysis Review"}).value
            == PaperPhase1State.APPROVED_BY_REVIEWER
        )
        assert (
            M.model_validate({"value": "Editorial Board Draft Sign-off"}).value
            == PaperPhase1State.LGP_APPROVED
        )

    def test_live_api_workflow_states(self) -> None:
        M = _model(PaperPhase1State)
        assert (
            M.model_validate({"value": "Editorial Board"}).value
            == PaperPhase1State.STARTED
        )
        assert (
            M.model_validate({"value": "Draft 1 Released to ATLAS"}).value
            == PaperPhase1State.REVIEW_CLOSED
        )


class TestPaperPhase2State:
    def test_human_readable_states(self) -> None:
        M = _model(PaperPhase2State)
        assert (
            M.model_validate({"value": "Phase 2 Data"}).value
            == PaperPhase2State.STARTED
        )
        assert (
            M.model_validate({"value": "Phase Closed"}).value
            == PaperPhase2State.FINISHED
        )

    def test_internal_workflow_states(self) -> None:
        M = _model(PaperPhase2State)
        assert (
            M.model_validate({"value": "Draft 2 Approval Process"}).value
            == PaperPhase2State.FINAL_REVIEW_CLOSED
        )
        assert (
            M.model_validate(
                {"value": "Revised Draft Final Sign-off by Editorial Board Chair"}
            ).value
            == PaperPhase2State.UPDATE_EDBOARD
        )

    def test_live_api_workflow_states(self) -> None:
        M = _model(PaperPhase2State)
        assert (
            M.model_validate(
                {
                    "value": "Revised Draft Final Sign-off by Publication Committee Chair or Deputy"
                }
            ).value
            == PaperPhase2State.UPDATED_PUBCOMM
        )

    def test_additional_workflow_states(self) -> None:
        M = _model(PaperPhase2State)
        assert (
            M.model_validate(
                {"value": "Final Sign-off by Spokesperson or Deputy"}
            ).value
            == PaperPhase2State.UPDATED_SPOKESPERSONDATE
        )


class TestPaperSubmissionState:
    def test_human_readable_states(self) -> None:
        M = _model(PaperSubmissionState)
        assert (
            M.model_validate({"value": "Publication Phase Launch"}).value
            == PaperSubmissionState.NOT_STARTED
        )
        assert (
            M.model_validate({"value": "Submission Closed"}).value
            == PaperSubmissionState.FINISHED
        )

    def test_internal_workflow_states(self) -> None:
        M = _model(PaperSubmissionState)
        assert (
            M.model_validate({"value": "Journal Submission"}).value
            == PaperSubmissionState.SUBMITTED_TO_ARXIV
        )
        assert (
            M.model_validate({"value": "Journal Reports Receiving"}).value
            == PaperSubmissionState.SUBMITTED_TO_JOURNAL
        )

    def test_live_api_workflow_states(self) -> None:
        M = _model(PaperSubmissionState)
        assert (
            M.model_validate({"value": "Journal Reports Answering"}).value
            == PaperSubmissionState.JOURNAL_REPORT_RECEIVED
        )
        assert (
            M.model_validate({"value": "Final ArXiv Replacement"}).value
            == PaperSubmissionState.PUBLISHED_ONLINE
        )

    def test_additional_workflow_states(self) -> None:
        M = _model(PaperSubmissionState)
        assert (
            M.model_validate({"value": "Erratum Submission"}).value
            == PaperSubmissionState.ERRATUM_REQUESTED
        )
        assert (
            M.model_validate({"value": "Paper Finish"}).value
            == PaperSubmissionState.FINAL_ARXIV_REPLACED
        )


class TestConfnotePhase1State:
    def test_human_readable_states(self) -> None:
        M = _model(ConfnotePhase1State)
        assert (
            M.model_validate({"value": "Phase 1 Data"}).value
            == ConfnotePhase1State.NOT_STARTED
        )
        assert (
            M.model_validate({"value": "Phase Closed"}).value
            == ConfnotePhase1State.FINISHED
        )
        assert (
            M.model_validate({"value": "CONF Release"}).value
            == ConfnotePhase1State.SECOND_SIGNED
        )

    def test_unknown_falls_back(self, caplog) -> None:
        M = _model(LenientConfnotePhase1State)
        with caplog.at_level(logging.WARNING, logger="stare"):
            result = M.model_validate({"value": "Some Future State"})
        assert result.value == "Some Future State"
        assert "ConfnotePhase1State" in caplog.text


# ---------------------------------------------------------------------------
# CollisionType
# ---------------------------------------------------------------------------


class TestCollisionType:
    def test_known_values(self) -> None:
        M = _model(LenientCollisionType)
        assert M.model_validate({"value": "p-p"}).value == CollisionType.PP
        assert M.model_validate({"value": "Pb-Pb"}).value == CollisionType.PB_PB
        assert M.model_validate({"value": "p-Pb"}).value == CollisionType.P_PB
        assert M.model_validate({"value": "Xe-Xe"}).value == CollisionType.XE_XE
        assert M.model_validate({"value": "Col type"}).value == CollisionType.COL_TYPE
        assert (
            M.model_validate({"value": "Sec col type"}).value
            == CollisionType.SEC_COL_TYPE
        )
        assert (
            M.model_validate({"value": "Tert col type"}).value
            == CollisionType.TERT_COL_TYPE
        )

    def test_unknown_falls_back(self, caplog) -> None:
        M = _model(LenientCollisionType)
        with caplog.at_level(logging.WARNING, logger="stare"):
            result = M.model_validate({"value": "n-n"})
        assert result.value == "n-n"
        assert "CollisionType" in caplog.text


# ---------------------------------------------------------------------------
# RepositoryType
# ---------------------------------------------------------------------------


class TestRepositoryType:
    def test_publication_shortcode_values(self) -> None:
        M = _model(LenientRepositoryType)
        assert M.model_validate({"value": "CONF"}).value == RepositoryType.CONF
        assert M.model_validate({"value": "INT"}).value == RepositoryType.INT
        assert M.model_validate({"value": "PAP"}).value == RepositoryType.PAP
        assert M.model_validate({"value": "PUB"}).value == RepositoryType.PUB

    def test_unknown_falls_back(self, caplog) -> None:
        M = _model(LenientRepositoryType)
        with caplog.at_level(logging.WARNING, logger="stare"):
            result = M.model_validate({"value": "software"})
        assert result.value == "software"
        assert "RepositoryType" in caplog.text


# ---------------------------------------------------------------------------
# PublicationType
# ---------------------------------------------------------------------------


class TestPublicationType:
    def test_known_values(self) -> None:
        M = _model(LenientPublicationType)
        assert M.model_validate({"value": "Paper"}).value == PublicationType.PAPER
        assert (
            M.model_validate({"value": "ConfNote"}).value == PublicationType.CONF_NOTE
        )
        assert M.model_validate({"value": "PubNote"}).value == PublicationType.PUB_NOTE
        assert M.model_validate({"value": "Analysis"}).value == PublicationType.ANALYSIS

    def test_unknown_falls_back(self, caplog) -> None:
        M = _model(LenientPublicationType)
        with caplog.at_level(logging.WARNING, logger="stare"):
            result = M.model_validate({"value": "Dataset"})
        assert result.value == "Dataset"
        assert "PublicationType" in caplog.text


# ---------------------------------------------------------------------------
# Non-string passthrough (enums should not crash on non-str inputs)
# ---------------------------------------------------------------------------


class TestNonStringPassthrough:
    def test_none_passes_through(self) -> None:
        M = _model(AnalysisStatus)
        assert M.model_validate({"value": None}).value is None

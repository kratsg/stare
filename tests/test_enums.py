"""Tests for lenient StrEnum types used in stare models."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel

from stare.models.enums import (
    AnalysisStatus,
    CollisionType,
    LenientCollisionType,
    LenientPublicationType,
    LenientRepositoryType,
    PaperStatus,
    Phase0State,
    Phase1State,
    Phase2State,
    PublicationType,
    RepositoryType,
    SubmissionState,
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
# PhaseState
# ---------------------------------------------------------------------------


class TestPhase0State:
    def test_human_readable_states(self) -> None:
        M = _model(Phase0State)
        assert (
            M.model_validate({"value": "Phase 0 Data"}).value == Phase0State.NOT_STARTED
        )
        assert (
            M.model_validate({"value": "Publications definition"}).value
            == Phase0State.FINISHED
        )

    def test_internal_workflow_states(self) -> None:
        M = _model(Phase0State)
        assert (
            M.model_validate({"value": "Approval acceptance"}).value
            == Phase0State.APPROVAL_ACCEPTANCE
        )
        assert (
            M.model_validate({"value": "Publication draft"}).value
            == Phase0State.PUBLICATION_DRAFT
        )

    def test_live_api_workflow_states(self) -> None:
        M = _model(Phase0State)
        assert (
            M.model_validate({"value": "Analysis definition after EOI meeting"}).value
            == Phase0State.ANALYSIS_DEFINITION
        )
        assert (
            M.model_validate({"value": "Skipped to CONF Note"}).value
            == Phase0State.CONF_SKIP
        )

    def test_additional_workflow_states(self) -> None:
        M = _model(Phase0State)
        assert (
            M.model_validate(
                {"value": "Analysis contact and expert review selection"}
            ).value
            == Phase0State.ANALYSIS_COORDINATORS_SELECTION
        )
        assert (
            M.model_validate({"value": "Analysis contacts' target date"}).value
            == Phase0State.ANALYSIS_COORDINATORS_TIMELINE
        )
        assert (
            M.model_validate({"value": "Approval meeting data"}).value
            == Phase0State.APPROVAL_MEETING_DATA
        )
        assert (
            M.model_validate(
                {"value": "Expression of interest (EOI) meeting data"}
            ).value
            == Phase0State.EOI_MEETING
        )
        assert (
            M.model_validate({"value": "Skipped to PUB Note"}).value
            == Phase0State.PUB_SKIP
        )


class TestPhase1State:
    def test_human_readable_states(self) -> None:
        M = _model(Phase1State)
        assert (
            M.model_validate({"value": "Phase 1 Data"}).value == Phase1State.NOT_STARTED
        )
        assert M.model_validate({"value": "Phase Closed"}).value == Phase1State.FINISHED

    def test_internal_workflow_states(self) -> None:
        M = _model(Phase1State)
        assert (
            M.model_validate({"value": "Analysis Review"}).value
            == Phase1State.APPROVED_BY_REVIEWER
        )
        assert (
            M.model_validate({"value": "Editorial Board Draft Sign-off"}).value
            == Phase1State.LGP_APPROVED
        )

    def test_live_api_workflow_states(self) -> None:
        M = _model(Phase1State)
        assert (
            M.model_validate({"value": "Editorial Board"}).value == Phase1State.STARTED
        )
        assert (
            M.model_validate({"value": "Draft 1 Released to ATLAS"}).value
            == Phase1State.REVIEW_CLOSED
        )


class TestPhase2State:
    def test_human_readable_states(self) -> None:
        M = _model(Phase2State)
        assert M.model_validate({"value": "Phase 2 Data"}).value == Phase2State.STARTED
        assert M.model_validate({"value": "Phase Closed"}).value == Phase2State.FINISHED

    def test_internal_workflow_states(self) -> None:
        M = _model(Phase2State)
        assert (
            M.model_validate({"value": "Draft 2 Approval Process"}).value
            == Phase2State.FINAL_REVIEW_CLOSED
        )
        assert (
            M.model_validate(
                {"value": "Revised Draft Final Sign-off by Editorial Board Chair"}
            ).value
            == Phase2State.UPDATE_EDBOARD
        )

    def test_live_api_workflow_states(self) -> None:
        M = _model(Phase2State)
        assert (
            M.model_validate(
                {
                    "value": "Revised Draft Final Sign-off by Publication Committee Chair or Deputy"
                }
            ).value
            == Phase2State.UPDATED_PUBCOMM
        )

    def test_additional_workflow_states(self) -> None:
        M = _model(Phase2State)
        assert (
            M.model_validate(
                {"value": "Final Sign-off by Spokesperson or Deputy"}
            ).value
            == Phase2State.UPDATED_SPOKESPERSONDATE
        )


class TestSubmissionState:
    def test_human_readable_states(self) -> None:
        M = _model(SubmissionState)
        assert (
            M.model_validate({"value": "Publication Phase Launch"}).value
            == SubmissionState.NOT_STARTED
        )
        assert (
            M.model_validate({"value": "Submission Closed"}).value
            == SubmissionState.FINISHED
        )

    def test_internal_workflow_states(self) -> None:
        M = _model(SubmissionState)
        assert (
            M.model_validate({"value": "Journal Submission"}).value
            == SubmissionState.SUBMITTED_TO_ARXIV
        )
        assert (
            M.model_validate({"value": "Journal Reports Receiving"}).value
            == SubmissionState.SUBMITTED_TO_JOURNAL
        )

    def test_live_api_workflow_states(self) -> None:
        M = _model(SubmissionState)
        assert (
            M.model_validate({"value": "Journal Reports Answering"}).value
            == SubmissionState.JOURNAL_REPORT_RECEIVED
        )
        assert (
            M.model_validate({"value": "Final ArXiv Replacement"}).value
            == SubmissionState.PUBLISHED_ONLINE
        )

    def test_additional_workflow_states(self) -> None:
        M = _model(SubmissionState)
        assert (
            M.model_validate({"value": "Erratum Submission"}).value
            == SubmissionState.ERRATUM_REQUESTED
        )
        assert (
            M.model_validate({"value": "Paper Finish"}).value
            == SubmissionState.FINAL_ARXIV_REPLACED
        )


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
    def test_known_values(self) -> None:
        M = _model(LenientRepositoryType)
        assert M.model_validate({"value": "analysis"}).value == RepositoryType.ANALYSIS
        assert M.model_validate({"value": "thesis"}).value == RepositoryType.THESIS
        assert (
            M.model_validate({"value": "framework"}).value == RepositoryType.FRAMEWORK
        )

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

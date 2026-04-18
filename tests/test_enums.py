"""Tests for lenient StrEnum types used in stare models."""

from __future__ import annotations

import logging

import pytest
from pydantic import BaseModel

from stare.models.enums import (
    AnalysisStatus,
    CollisionType,
    PaperStatus,
    PhaseState,
    PublicationType,
    RepositoryType,
    LenientAnalysisStatus,
    LenientCollisionType,
    LenientPaperStatus,
    LenientPhaseState,
    LenientPublicationType,
    LenientRepositoryType,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _model(lenient_type):
    """Return a tiny pydantic model with a single `value` field of the given type."""

    class M(BaseModel):
        value: lenient_type | None = None  # type: ignore[valid-type]

    return M


# ---------------------------------------------------------------------------
# AnalysisStatus
# ---------------------------------------------------------------------------


class TestAnalysisStatus:
    def test_known_values_parse(self) -> None:
        M = _model(LenientAnalysisStatus)
        assert M.model_validate({"value": "Active"}).value == AnalysisStatus.ACTIVE
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

    def test_unknown_value_falls_back_to_str(self, caplog) -> None:
        M = _model(LenientAnalysisStatus)
        with caplog.at_level(logging.WARNING, logger="stare"):
            result = M.model_validate({"value": "Future Status"})
        assert result.value == "Future Status"
        assert "AnalysisStatus" in caplog.text
        assert "Future Status" in caplog.text

    def test_enum_compares_equal_to_string(self) -> None:
        assert AnalysisStatus.ACTIVE == "Active"

    def test_round_trip(self) -> None:
        M = _model(LenientAnalysisStatus)
        m = M.model_validate({"value": "Active"})
        dumped = m.model_dump()
        assert dumped["value"] == "Active"

    def test_none_default(self) -> None:
        M = _model(LenientAnalysisStatus)
        assert M.model_validate({}).value is None


# ---------------------------------------------------------------------------
# PaperStatus
# ---------------------------------------------------------------------------


class TestPaperStatus:
    def test_known_values_parse(self) -> None:
        M = _model(LenientPaperStatus)
        assert M.model_validate({"value": "Active"}).value == PaperStatus.ACTIVE
        assert (
            M.model_validate({"value": "Submission Closed"}).value
            == PaperStatus.SUBMISSION_CLOSED
        )

    def test_unknown_value_falls_back(self, caplog) -> None:
        M = _model(LenientPaperStatus)
        with caplog.at_level(logging.WARNING, logger="stare"):
            result = M.model_validate({"value": "Unknown"})
        assert result.value == "Unknown"
        assert "PaperStatus" in caplog.text


# ---------------------------------------------------------------------------
# PhaseState
# ---------------------------------------------------------------------------


class TestPhaseState:
    def test_human_readable_states(self) -> None:
        M = _model(LenientPhaseState)
        assert M.model_validate({"value": "Active"}).value == PhaseState.ACTIVE
        assert M.model_validate({"value": "Approved"}).value == PhaseState.APPROVED
        assert M.model_validate({"value": "finished"}).value == PhaseState.FINISHED

    def test_internal_workflow_states(self) -> None:
        M = _model(LenientPhaseState)
        assert (
            M.model_validate({"value": "approval_acceptance"}).value
            == PhaseState.APPROVAL_ACCEPTANCE
        )
        assert (
            M.model_validate({"value": "publication_draft"}).value
            == PhaseState.PUBLICATION_DRAFT
        )

    def test_unknown_state_falls_back(self, caplog) -> None:
        M = _model(LenientPhaseState)
        with caplog.at_level(logging.WARNING, logger="stare"):
            result = M.model_validate({"value": "some_future_state"})
        assert result.value == "some_future_state"
        assert "PhaseState" in caplog.text


# ---------------------------------------------------------------------------
# CollisionType
# ---------------------------------------------------------------------------


class TestCollisionType:
    def test_known_values(self) -> None:
        M = _model(LenientCollisionType)
        assert M.model_validate({"value": "p-p"}).value == CollisionType.PP
        assert M.model_validate({"value": "Pb-Pb"}).value == CollisionType.PBPB

    def test_unknown_falls_back(self, caplog) -> None:
        M = _model(LenientCollisionType)
        with caplog.at_level(logging.WARNING, logger="stare"):
            result = M.model_validate({"value": "p-Pb"})
        assert result.value == "p-Pb"
        assert "CollisionType" in caplog.text


# ---------------------------------------------------------------------------
# RepositoryType
# ---------------------------------------------------------------------------


class TestRepositoryType:
    def test_known_values(self) -> None:
        M = _model(LenientRepositoryType)
        assert (
            M.model_validate({"value": "analysis"}).value == RepositoryType.ANALYSIS
        )
        assert M.model_validate({"value": "thesis"}).value == RepositoryType.THESIS
        assert (
            M.model_validate({"value": "framework"}).value == RepositoryType.FRAMEWORK
        )

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
        assert (
            M.model_validate({"value": "PubNote"}).value == PublicationType.PUB_NOTE
        )
        assert (
            M.model_validate({"value": "Analysis"}).value == PublicationType.ANALYSIS
        )

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
        M = _model(LenientAnalysisStatus)
        assert M.model_validate({"value": None}).value is None


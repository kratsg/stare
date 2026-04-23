"""Tests for FieldRegistry normalization and validation."""

from __future__ import annotations

import pytest

from stare.dsl.errors import DSLValidationError
from stare.dsl.registry import FieldRegistry


@pytest.fixture
def analysis_reg() -> FieldRegistry:
    return FieldRegistry.for_mode("analysis")


@pytest.fixture
def paper_reg() -> FieldRegistry:
    return FieldRegistry.for_mode("paper")


def test_known_camel_field_normalizes(analysis_reg: FieldRegistry) -> None:
    assert analysis_reg.normalize("referenceCode") == "referenceCode"


def test_snake_case_normalizes_to_camel(analysis_reg: FieldRegistry) -> None:
    assert analysis_reg.normalize("reference_code") == "referenceCode"


def test_nested_camel_normalizes(analysis_reg: FieldRegistry) -> None:
    assert analysis_reg.normalize("metadata.keywords") == "metadata.keywords"


def test_nested_snake_normalizes(analysis_reg: FieldRegistry) -> None:
    assert analysis_reg.normalize("metadata.mva_ml_tools") == "metadata.mvaMlTools"


def test_nested_deep_snake(analysis_reg: FieldRegistry) -> None:
    assert (
        analysis_reg.normalize("phase0.editorial_board_formed_on")
        == "phase0.editorialBoardFormedOn"
    )


def test_known_field_validates(analysis_reg: FieldRegistry) -> None:
    analysis_reg.validate("referenceCode")


def test_unknown_field_raises(analysis_reg: FieldRegistry) -> None:
    with pytest.raises(DSLValidationError, match="unknown field 'foo'"):
        analysis_reg.validate("foo")


def test_close_match_suggested(analysis_reg: FieldRegistry) -> None:
    with pytest.raises(DSLValidationError, match="did you mean 'referenceCode'"):
        analysis_reg.validate("referenceCodes")


def test_paper_mode_has_full_title(paper_reg: FieldRegistry) -> None:
    assert paper_reg.normalize("fullTitle") == "fullTitle"
    paper_reg.validate("fullTitle")


def test_analysis_only_field_rejected_by_paper(paper_reg: FieldRegistry) -> None:
    with pytest.raises(DSLValidationError, match="unknown field"):
        paper_reg.validate("phase0.state")


def test_paper_only_field_rejected_by_analysis(analysis_reg: FieldRegistry) -> None:
    with pytest.raises(DSLValidationError, match="unknown field"):
        analysis_reg.validate("fullTitle")


def test_registry_loads_pubnote_mode() -> None:
    reg = FieldRegistry.for_mode("pubnote")
    assert "finalReferenceCode" in reg.fields()
    assert "shortTitle" in reg.fields()
    assert "phase1.state" in reg.fields()

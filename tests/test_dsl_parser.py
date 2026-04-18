"""End-to-end tests for parse_dsl()."""

from __future__ import annotations

import pytest

from stare.dsl import DSLSyntaxError, DSLValidationError, parse_dsl
from stare.dsl.models import And, Condition, Or


def test_simple_equality() -> None:
    expr = parse_dsl("referenceCode = HION", mode="analysis")
    assert isinstance(expr, Condition)
    assert expr.field == "referenceCode"
    assert expr.operator == "="
    assert expr.value == "HION"


def test_contain_operator() -> None:
    expr = parse_dsl("metadata.keywords contain jets", mode="analysis")
    assert isinstance(expr, Condition)
    assert expr.operator == "contain"
    assert expr.value == "jets"


def test_snake_case_normalized() -> None:
    expr = parse_dsl("reference_code = HION", mode="analysis")
    assert isinstance(expr, Condition)
    assert expr.field == "referenceCode"


def test_nested_snake_normalized() -> None:
    expr = parse_dsl("metadata.mva_ml_tools contain jets", mode="analysis")
    assert isinstance(expr, Condition)
    assert expr.field == "metadata.mvaMlTools"


def test_and_expression() -> None:
    expr = parse_dsl("referenceCode = HION and status = ACTIVE", mode="analysis")
    assert isinstance(expr, And)
    assert len(expr.clauses) == 2


def test_or_expression() -> None:
    expr = parse_dsl("status = ACTIVE or status = PENDING", mode="analysis")
    assert isinstance(expr, Or)
    assert len(expr.clauses) == 2


def test_round_trip_canonicalizes_case() -> None:
    src_in = "(status = ACTIVE OR status = PENDING) AND metadata.keywords contain jets"
    src_out = "(status = ACTIVE or status = PENDING) and metadata.keywords contain jets"
    expr = parse_dsl(src_in, mode="analysis")
    assert expr.to_dsl() == src_out


def test_canonical_form_is_idempotent() -> None:
    src = "(status = ACTIVE or status = PENDING) and metadata.keywords contain jets"
    assert parse_dsl(src, mode="analysis").to_dsl() == src


def test_unknown_field_raises_validation_error() -> None:
    with pytest.raises(DSLValidationError, match="unknown field 'foo'"):
        parse_dsl("foo = bar", mode="analysis")


def test_syntax_error_raises_dsl_syntax_error() -> None:
    with pytest.raises(DSLSyntaxError):
        parse_dsl("referenceCode", mode="analysis")


def test_syntax_error_message_contains_context() -> None:
    with pytest.raises(DSLSyntaxError, match="referenceCode"):
        parse_dsl("referenceCode", mode="analysis")


def test_paper_specific_field_accepted() -> None:
    expr = parse_dsl("fullTitle contain Higgs", mode="paper")
    assert isinstance(expr, Condition)
    assert expr.field == "fullTitle"


def test_analysis_field_rejected_in_paper_mode() -> None:
    with pytest.raises(DSLValidationError):
        parse_dsl("phase0.state = ACTIVE", mode="paper")


def test_paper_field_rejected_in_analysis_mode() -> None:
    with pytest.raises(DSLValidationError):
        parse_dsl("fullTitle contain Higgs", mode="analysis")

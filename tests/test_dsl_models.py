"""Tests for the DSL AST models and to_dsl() serializers."""

from __future__ import annotations

import pytest

from stare.dsl import parse_dsl
from stare.dsl.models import And, Condition, Operator, Or


def test_operator_is_str_enum() -> None:
    assert issubclass(Operator, str)
    assert Operator("=") is Operator.EQ
    assert Operator("contain") is Operator.CONTAIN


def test_condition_operator_is_enum_member() -> None:
    c = Condition.model_validate({"field": "f", "operator": Operator.EQ, "value": "v"})
    assert isinstance(c.operator, Operator)


def test_condition_to_dsl() -> None:
    c = Condition.model_validate(
        {"field": "referenceCode", "operator": Operator.EQ, "value": "HION"}
    )
    assert c.to_dsl() == "referenceCode = HION"


def test_condition_hyphenated_value() -> None:
    c = Condition.model_validate(
        {"field": "referenceCode", "operator": Operator.EQ, "value": "ANA-HION-2018-01"}
    )
    assert c.to_dsl() == "referenceCode = ANA-HION-2018-01"


def test_and_two_clauses() -> None:
    expr = And(
        clauses=(
            Condition.model_validate(
                {"field": "a", "operator": Operator.EQ, "value": "x"}
            ),
            Condition.model_validate(
                {"field": "b", "operator": Operator.CONTAIN, "value": "y"}
            ),
        )
    )
    assert expr.to_dsl() == "a = x AND b contain y"


def test_or_two_clauses() -> None:
    expr = Or(
        clauses=(
            Condition.model_validate(
                {"field": "status", "operator": Operator.EQ, "value": "ACTIVE"}
            ),
            Condition.model_validate(
                {"field": "status", "operator": Operator.EQ, "value": "PENDING"}
            ),
        )
    )
    assert expr.to_dsl() == "status = ACTIVE OR status = PENDING"


def test_or_inside_and_no_parens() -> None:
    inner = Or(
        clauses=(
            Condition.model_validate(
                {"field": "status", "operator": Operator.EQ, "value": "ACTIVE"}
            ),
            Condition.model_validate(
                {"field": "status", "operator": Operator.EQ, "value": "PENDING"}
            ),
        )
    )
    outer = And(
        clauses=(
            inner,
            Condition.model_validate(
                {"field": "keywords", "operator": Operator.CONTAIN, "value": "jets"}
            ),
        )
    )
    assert (
        outer.to_dsl()
        == "status = ACTIVE OR status = PENDING AND keywords contain jets"
    )


def test_and_inside_or_no_parens() -> None:
    inner = And(
        clauses=(
            Condition.model_validate(
                {"field": "a", "operator": Operator.EQ, "value": "x"}
            ),
            Condition.model_validate(
                {"field": "b", "operator": Operator.EQ, "value": "y"}
            ),
        )
    )
    outer = Or(
        clauses=(
            inner,
            Condition.model_validate(
                {"field": "c", "operator": Operator.EQ, "value": "z"}
            ),
        )
    )
    assert outer.to_dsl() == "a = x AND b = y OR c = z"


@pytest.mark.parametrize("op", list(Operator))
def test_all_operators(op: Operator) -> None:
    c = Condition.model_validate({"field": "f", "operator": op, "value": "v"})
    assert op.value in c.to_dsl()


def test_multiword_value_quoted_in_dsl() -> None:
    """Values containing whitespace are wrapped in double-quotes by to_dsl()."""
    c = Condition.model_validate(
        {"field": "shortTitle", "operator": Operator.EQ, "value": "Phase Closed"}
    )
    assert c.to_dsl() == 'shortTitle = "Phase Closed"'


def test_value_with_embedded_quote_raises() -> None:
    """to_dsl raises ValueError when self.value contains a double-quote."""
    c = Condition.model_validate(
        {"field": "shortTitle", "operator": Operator.EQ, "value": 'has"quote'}
    )
    with pytest.raises(ValueError, match=r"embedded.*quote|not.*supported|to_dsl"):
        c.to_dsl()


@pytest.mark.parametrize(
    ("value", "expected", "msg"),
    [
        ("", '""', "empty string must be quoted"),
        ("Phase Closed", '"Phase Closed"', "space triggers quoting"),
        ("has(paren)", '"has(paren)"', "opening paren triggers quoting"),
        ("has[bracket]", '"has[bracket]"', "opening bracket triggers quoting"),
    ],
)
def test_value_quoted_when_needed(value: str, expected: str, msg: str) -> None:
    """to_dsl wraps values that are empty, contain spaces, or contain delimiter chars."""
    c = Condition.model_validate(
        {"field": "f", "operator": Operator.EQ, "value": value}
    )
    assert c.to_dsl() == f"f = {expected}", msg


@pytest.mark.parametrize("value", ["has\nnewline", "has\ffeed", "has\ttab"])
def test_value_with_non_space_whitespace_raises(value: str) -> None:
    """to_dsl raises ValueError for non-space whitespace characters."""
    c = Condition.model_validate(
        {"field": "f", "operator": Operator.EQ, "value": value}
    )
    with pytest.raises(ValueError, match="non-space whitespace"):
        c.to_dsl()


def test_multiword_value_round_trips() -> None:
    """parse_dsl → to_dsl is idempotent for double-quoted multi-word values."""
    src = 'shortTitle = "Phase Closed"'
    expr = parse_dsl(src, mode="analysis")
    assert expr.to_dsl() == src
    assert parse_dsl(expr.to_dsl(), mode="analysis").to_dsl() == src


@pytest.mark.parametrize(
    ("src", "canonical", "msg"),
    [
        (
            '"shortTitle" = "Phase Closed"',
            'shortTitle = "Phase Closed"',
            "quoted field unquoted in canonical output, multi-word value stays quoted",
        ),
        (
            '"reference_code" = HION',
            "referenceCode = HION",
            "quoted snake_case field normalizes to camelCase, bare value stays bare",
        ),
        (
            '"phase0.state" = "ACTIVE"',
            "phase0.state = ACTIVE",
            "quoted single-token value is unquoted in canonical output",
        ),
    ],
)
def test_quoted_field_round_trip(src: str, canonical: str, msg: str) -> None:
    """Quoted fields are normalized/unquoted in to_dsl() output; round-trip is idempotent."""
    expr = parse_dsl(src, mode="analysis")
    assert expr.to_dsl() == canonical, msg
    assert parse_dsl(expr.to_dsl(), mode="analysis").to_dsl() == canonical, msg

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
    c = Condition(field="f", operator=Operator.EQ, value="v")
    assert isinstance(c.operator, Operator)


def test_condition_to_dsl() -> None:
    c = Condition(field="referenceCode", operator=Operator.EQ, value="HION")
    assert c.to_dsl() == "referenceCode = HION"


def test_condition_hyphenated_value() -> None:
    c = Condition(field="referenceCode", operator=Operator.EQ, value="ANA-HION-2018-01")
    assert c.to_dsl() == "referenceCode = ANA-HION-2018-01"


def test_and_two_clauses() -> None:
    expr = And(
        clauses=(
            Condition(field="a", operator=Operator.EQ, value="x"),
            Condition(field="b", operator=Operator.CONTAIN, value="y"),
        )
    )
    assert expr.to_dsl() == "a = x AND b contain y"


def test_or_two_clauses() -> None:
    expr = Or(
        clauses=(
            Condition(field="status", operator=Operator.EQ, value="ACTIVE"),
            Condition(field="status", operator=Operator.EQ, value="PENDING"),
        )
    )
    assert expr.to_dsl() == "status = ACTIVE OR status = PENDING"


def test_or_inside_and_no_parens() -> None:
    inner = Or(
        clauses=(
            Condition(field="status", operator=Operator.EQ, value="ACTIVE"),
            Condition(field="status", operator=Operator.EQ, value="PENDING"),
        )
    )
    outer = And(
        clauses=(
            inner,
            Condition(field="keywords", operator=Operator.CONTAIN, value="jets"),
        )
    )
    assert (
        outer.to_dsl()
        == "status = ACTIVE OR status = PENDING AND keywords contain jets"
    )


def test_and_inside_or_no_parens() -> None:
    inner = And(
        clauses=(
            Condition(field="a", operator=Operator.EQ, value="x"),
            Condition(field="b", operator=Operator.EQ, value="y"),
        )
    )
    outer = Or(clauses=(inner, Condition(field="c", operator=Operator.EQ, value="z")))
    assert outer.to_dsl() == "a = x AND b = y OR c = z"


@pytest.mark.parametrize("op", list(Operator))
def test_all_operators(op: Operator) -> None:
    c = Condition(field="f", operator=op, value="v")
    assert op.value in c.to_dsl()


def test_multiword_value_quoted_in_dsl() -> None:
    """Values containing whitespace are wrapped in double-quotes by to_dsl()."""
    c = Condition(field="shortTitle", operator=Operator.EQ, value="Phase Closed")
    assert c.to_dsl() == 'shortTitle = "Phase Closed"'


def test_value_with_embedded_quote_raises() -> None:
    """to_dsl raises ValueError when self.value contains a double-quote."""
    c = Condition(field="shortTitle", operator=Operator.EQ, value='has"quote')
    with pytest.raises(ValueError, match=r"embedded.*quote|not.*supported|to_dsl"):
        c.to_dsl()


def test_bare_value_stays_bare() -> None:
    """Single-token values without special chars are emitted without quotes."""
    c = Condition(field="referenceCode", operator=Operator.EQ, value="HION")
    assert c.to_dsl() == "referenceCode = HION"


def test_multiword_value_round_trips() -> None:
    """parse_dsl → to_dsl is idempotent for double-quoted multi-word values."""
    src = 'shortTitle = "Phase Closed"'
    expr = parse_dsl(src, mode="analysis")
    assert expr.to_dsl() == src
    assert parse_dsl(expr.to_dsl(), mode="analysis").to_dsl() == src

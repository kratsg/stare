"""Tests for the DSL AST models and to_dsl() serializers."""
from __future__ import annotations

import pytest

from stare.dsl.models import And, Condition, Or


def test_condition_to_dsl() -> None:
    c = Condition(field="referenceCode", operator="=", value="HION")
    assert c.to_dsl() == "referenceCode = HION"


def test_condition_hyphenated_value() -> None:
    c = Condition(field="referenceCode", operator="=", value="ANA-HION-2018-01")
    assert c.to_dsl() == "referenceCode = ANA-HION-2018-01"


def test_and_two_clauses() -> None:
    expr = And(
        clauses=[
            Condition(field="a", operator="=", value="x"),
            Condition(field="b", operator="contain", value="y"),
        ]
    )
    assert expr.to_dsl() == "a = x and b contain y"


def test_or_two_clauses() -> None:
    expr = Or(
        clauses=[
            Condition(field="status", operator="=", value="ACTIVE"),
            Condition(field="status", operator="=", value="PENDING"),
        ]
    )
    assert expr.to_dsl() == "status = ACTIVE or status = PENDING"


def test_or_parenthesized_inside_and() -> None:
    inner = Or(
        clauses=[
            Condition(field="status", operator="=", value="ACTIVE"),
            Condition(field="status", operator="=", value="PENDING"),
        ]
    )
    outer = And(
        clauses=[
            inner,
            Condition(field="keywords", operator="contain", value="jets"),
        ]
    )
    assert outer.to_dsl() == (
        "(status = ACTIVE or status = PENDING) and keywords contain jets"
    )


def test_and_inside_or_not_parenthesized() -> None:
    inner = And(
        clauses=[
            Condition(field="a", operator="=", value="x"),
            Condition(field="b", operator="=", value="y"),
        ]
    )
    outer = Or(clauses=[inner, Condition(field="c", operator="=", value="z")])
    assert outer.to_dsl() == "a = x and b = y or c = z"


@pytest.mark.parametrize("op", ["=", "!=", "contain", "not-contain"])
def test_all_operators(op: str) -> None:
    c = Condition(field="f", operator=op, value="v")  # type: ignore[arg-type]
    assert op in c.to_dsl()

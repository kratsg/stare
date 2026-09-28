"""Tests for the DSL AST models and to_dsl() serializers."""

from __future__ import annotations

import re

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


def test_or_inside_and_is_parenthesized() -> None:
    """AND binds tighter than OR on the server, so an Or operand of an And must
    be grouped, or the query changes meaning."""
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
        == "( status = ACTIVE OR status = PENDING ) AND keywords contain jets"
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


def test_empty_sentinel_emitted_bare() -> None:
    """__EMPTY__ contains no special chars, so to_dsl() emits it unquoted."""
    c = Condition.model_validate(
        {"field": "publicShortTitle", "operator": Operator.EQ, "value": "__EMPTY__"}
    )
    assert c.to_dsl() == "publicShortTitle = __EMPTY__"


@pytest.mark.parametrize(
    "value", ["and", "or", "AND", "Or", "contain", "not-contain", "=", "!="]
)
def test_reserved_token_value_quoted(value: str) -> None:
    """Values equal to DSL keywords/operators are quoted so they round-trip."""
    c = Condition.model_validate(
        {"field": "shortTitle", "operator": Operator.EQ, "value": value}
    )
    assert c.to_dsl() == f'shortTitle = "{value}"'
    reparsed = parse_dsl(c.to_dsl(), mode="analysis")
    assert isinstance(reparsed, Condition)
    assert reparsed.value == value


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


def _c(field: str, value: str, op: Operator = Operator.EQ) -> Condition:
    return Condition(field=field, operator=op, value=value)


def test_or_on_right_of_and_is_parenthesized() -> None:
    expr = And(clauses=(_c("a", "x"), Or(clauses=(_c("b", "y"), _c("c", "z")))))
    assert expr.to_dsl() == "a = x AND ( b = y OR c = z )"


def test_or_on_both_sides_of_and_is_parenthesized() -> None:
    expr = And(
        clauses=(
            Or(clauses=(_c("a", "1"), _c("a", "2"))),
            Or(clauses=(_c("b", "1"), _c("b", "2"))),
        )
    )
    assert expr.to_dsl() == "( a = 1 OR a = 2 ) AND ( b = 1 OR b = 2 )"


def test_or_nested_in_and_nested_in_and_is_parenthesized() -> None:
    inner = And(clauses=(_c("a", "x"), Or(clauses=(_c("b", "y"), _c("c", "z")))))
    expr = And(clauses=(inner, _c("d", "w")))
    assert expr.to_dsl() == "a = x AND ( b = y OR c = z ) AND d = w"


def test_or_inside_or_is_not_parenthesized() -> None:
    expr = Or(clauses=(Or(clauses=(_c("a", "1"), _c("a", "2"))), _c("a", "3")))
    assert expr.to_dsl() == "a = 1 OR a = 2 OR a = 3"


def test_and_containing_grouped_or_inside_or() -> None:
    grouped = And(clauses=(_c("a", "x"), Or(clauses=(_c("b", "y"), _c("c", "z")))))
    expr = Or(clauses=(grouped, _c("d", "w")))
    assert expr.to_dsl() == "a = x AND ( b = y OR c = z ) OR d = w"


def test_parentheses_are_space_padded() -> None:
    """Glance glues a parenthesis onto an adjacent bare token and returns HTTP
    500 (ATGLANCE-8337), so every emitted parenthesis must be space-padded."""
    expr = And(
        clauses=(
            Or(clauses=(_c("a", "1"), _c("a", "2"))),
            Or(clauses=(_c("b", "1"), _c("b", "quoted value"))),
        )
    )
    dsl = expr.to_dsl()
    assert "(" in dsl
    assert not re.search(r"\((?! )|(?<! )\)", dsl), dsl

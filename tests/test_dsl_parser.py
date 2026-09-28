"""End-to-end tests for parse_dsl()."""

from __future__ import annotations

import logging
import sys

import pytest

from stare.dsl import DSLSyntaxError, DSLValidationError, parse_dsl
from stare.dsl.models import And, Condition, Operator, Or


def test_simple_equality() -> None:
    expr = parse_dsl("referenceCode = HION", mode="analysis")
    assert isinstance(expr, Condition)
    assert expr.field == "referenceCode"
    assert expr.operator == "="
    assert expr.value == "HION"


def test_contain_operator() -> None:
    expr = parse_dsl("metadata.keywords.name contain jets", mode="analysis")
    assert isinstance(expr, Condition)
    assert expr.operator == "contain"
    assert expr.value == "jets"


def test_snake_case_normalized() -> None:
    expr = parse_dsl("reference_code = HION", mode="analysis")
    assert isinstance(expr, Condition)
    assert expr.field == "referenceCode"


def test_nested_snake_normalized() -> None:
    expr = parse_dsl("metadata.mva_ml_tools.name contain jets", mode="analysis")
    assert isinstance(expr, Condition)
    assert expr.field == "metadata.mvaMlTools.name"


def test_and_expression() -> None:
    expr = parse_dsl("referenceCode = HION and status = ACTIVE", mode="analysis")
    assert isinstance(expr, And)
    assert len(expr.clauses) == 2


def test_or_expression() -> None:
    expr = parse_dsl("status = ACTIVE or status = PENDING", mode="analysis")
    assert isinstance(expr, Or)
    assert len(expr.clauses) == 2


def test_round_trip_canonicalizes_case() -> None:
    """Mixed-case and/or input is normalized to uppercase AND/OR in output."""
    src_in = (
        "status = ACTIVE or status = PENDING and metadata.keywords.name contain jets"
    )
    src_out = (
        "status = ACTIVE OR status = PENDING AND metadata.keywords.name contain jets"
    )
    expr = parse_dsl(src_in, mode="analysis")
    assert expr.to_dsl() == src_out


def test_canonical_form_is_idempotent() -> None:
    src = "status = ACTIVE OR status = PENDING AND metadata.keywords.name contain jets"
    assert parse_dsl(src, mode="analysis").to_dsl() == src


def test_parentheses_do_not_warn(caplog: pytest.LogCaptureFixture) -> None:
    """Grouping is preserved when serialized, so parentheses are not warned about."""
    with caplog.at_level(logging.WARNING, logger="stare"):
        parse_dsl("(referenceCode = HION)", mode="analysis")
    assert "parenthes" not in caplog.text.lower()


def test_parens_in_quoted_value_do_not_warn(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Parentheses inside a quoted string value must not trigger the warning."""
    with caplog.at_level(logging.WARNING, logger="stare"):
        expr = parse_dsl('shortTitle = "foo (bar)"', mode="analysis")
    assert "parenthes" not in caplog.text.lower()
    assert isinstance(expr, Condition)
    assert expr.value == "foo (bar)"


def test_parentheses_that_change_grouping_are_preserved() -> None:
    """An OR grouped inside an AND keeps its (space-padded) parentheses."""
    expr = parse_dsl(
        "(status = ACTIVE OR status = PENDING) AND referenceCode = HION",
        mode="analysis",
    )
    assert (
        expr.to_dsl()
        == "( status = ACTIVE OR status = PENDING ) AND referenceCode = HION"
    )


@pytest.mark.parametrize(
    ("src", "canonical"),
    [
        ("(referenceCode = HION)", "referenceCode = HION"),
        (
            "(status = ACTIVE AND referenceCode = HION) OR status = PENDING",
            "status = ACTIVE AND referenceCode = HION OR status = PENDING",
        ),
        (
            "status = ACTIVE OR (status = PENDING OR status = CLOSED)",
            "status = ACTIVE OR status = PENDING OR status = CLOSED",
        ),
    ],
)
def test_redundant_parentheses_are_dropped(src: str, canonical: str) -> None:
    assert parse_dsl(src, mode="analysis").to_dsl() == canonical


def test_grouped_canonical_form_is_idempotent() -> None:
    src = "( status = ACTIVE OR status = PENDING ) AND referenceCode = HION"
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


def test_syntax_error_bad_op_hints_valid_operators() -> None:
    """Unknown operator name triggers a hint listing valid operators."""
    with pytest.raises(DSLSyntaxError, match="contain"):
        parse_dsl("fullTitle badop Higgs", mode="paper")


def test_syntax_error_contains_typo_hints_contain() -> None:
    """'contains' (wrong suffix) is detected and 'contain' is suggested."""
    with pytest.raises(DSLSyntaxError, match="contain"):
        parse_dsl("fullTitle contains Higgs", mode="paper")


def test_syntax_error_extra_token_hints_and_or() -> None:
    """Extra token after a complete condition suggests AND/OR chaining."""
    with pytest.raises(DSLSyntaxError, match=r"(?i)and.*or|or.*and"):
        parse_dsl("fullTitle contain Higgs extra", mode="paper")


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


def test_quoted_value_stripped() -> None:
    """A double-quoted value is stripped to the inner string."""
    expr = parse_dsl('shortTitle = "Phase Closed"', mode="analysis")
    assert isinstance(expr, Condition)
    assert expr.field == "shortTitle"
    assert expr.value == "Phase Closed"


def test_quoted_field_stripped() -> None:
    """A double-quoted field is stripped and normalized as usual."""
    expr = parse_dsl('"phase0.state" = ACTIVE', mode="analysis")
    assert isinstance(expr, Condition)
    assert expr.field == "phase0.state"
    assert expr.value == "ACTIVE"


def test_quoted_field_and_value() -> None:
    """Both field and value may be double-quoted simultaneously."""
    expr = parse_dsl('"phase0.state" = "ACTIVE"', mode="analysis")
    assert isinstance(expr, Condition)
    assert expr.field == "phase0.state"
    assert expr.value == "ACTIVE"


def test_quoted_snake_case_field_normalizes() -> None:
    """A quoted snake_case field still normalizes to camelCase."""
    expr = parse_dsl('"reference_code" = HION', mode="analysis")
    assert isinstance(expr, Condition)
    assert expr.field == "referenceCode"


# --- boolean field operator restriction ---


def test_boolean_field_with_eq_accepted() -> None:
    expr = parse_dsl('"analysisTeam.isContactEditor" = "true"', mode="analysis")
    assert isinstance(expr, Condition)
    assert expr.field == "analysisTeam.isContactEditor"


def test_boolean_field_with_ne_accepted() -> None:
    expr = parse_dsl('"analysisTeam.isContactEditor" != "false"', mode="analysis")
    assert isinstance(expr, Condition)
    assert expr.field == "analysisTeam.isContactEditor"


def test_boolean_field_with_contain_raises() -> None:
    with pytest.raises(DSLValidationError, match="isContactEditor"):
        parse_dsl('"analysisTeam.isContactEditor" contain "true"', mode="analysis")


def test_boolean_field_with_not_contain_raises() -> None:
    with pytest.raises(DSLValidationError, match="isContactEditor"):
        parse_dsl('"analysisTeam.isContactEditor" not-contain "true"', mode="analysis")


# --- __EMPTY__ NULL sentinel ---


def test_empty_sentinel_quoted() -> None:
    expr = parse_dsl('publicShortTitle = "__EMPTY__"', mode="analysis")
    assert isinstance(expr, Condition)
    assert expr.field == "publicShortTitle"
    assert expr.operator == "="
    assert expr.value == "__EMPTY__"


def test_empty_sentinel_bare() -> None:
    expr = parse_dsl("publicShortTitle = __EMPTY__", mode="analysis")
    assert isinstance(expr, Condition)
    assert expr.value == "__EMPTY__"


def test_empty_sentinel_ne_operator() -> None:
    expr = parse_dsl('shortTitle != "__EMPTY__"', mode="analysis")
    assert isinstance(expr, Condition)
    assert expr.operator == "!="
    assert expr.value == "__EMPTY__"


def test_paper_boolean_field_operator_restriction() -> None:
    with pytest.raises(DSLValidationError):
        parse_dsl(
            '"phase2.preliminaryPlotsAndResultsReleased" contain "true"', mode="paper"
        )


def test_pubnote_boolean_field_operator_restriction() -> None:
    with pytest.raises(DSLValidationError):
        parse_dsl('"phase1.readers.isFirstReader" contain "true"', mode="pubnote")


# --- list membership: in / not in ---


def test_in_single_value_is_plain_condition() -> None:
    expr = parse_dsl("status in [Active]", mode="analysis")
    assert expr == Condition(field="status", operator=Operator.EQ, value="Active")


def test_in_expands_to_or_of_equalities() -> None:
    expr = parse_dsl("reference_code in [A, B, C]", mode="analysis")
    eq = [
        Condition(field="referenceCode", operator=Operator.EQ, value=v)
        for v in ("A", "B", "C")
    ]
    assert expr == Or(clauses=(Or(clauses=(eq[0], eq[1])), eq[2]))
    assert (
        expr.to_dsl() == "referenceCode = A OR referenceCode = B OR referenceCode = C"
    )


def test_not_in_expands_to_and_of_inequalities() -> None:
    expr = parse_dsl("status NOT IN [Closed, Archived]", mode="analysis")
    ne = [
        Condition(field="status", operator=Operator.NE, value=v)
        for v in ("Closed", "Archived")
    ]
    assert expr == And(clauses=(ne[0], ne[1]))
    assert expr.to_dsl() == "status != Closed AND status != Archived"


def test_in_quoted_values_keep_commas_and_spaces() -> None:
    expr = parse_dsl('shortTitle in ["a, b", "two words", bare]', mode="analysis")
    assert expr.to_dsl() == (
        'shortTitle = "a, b" OR shortTitle = "two words" OR shortTitle = bare'
    )


def test_in_combined_with_and_is_grouped() -> None:
    """The motivating example from #81: the Or chain is grouped under AND."""
    groups = ["EGAM", "MUON", "JETM"]
    expr = parse_dsl(
        f"status != Closed AND groups.leadingGroup.name in [{', '.join(groups)}]",
        mode="analysis",
    )
    assert expr.to_dsl() == (
        "status != Closed AND ( groups.leadingGroup.name = EGAM"
        " OR groups.leadingGroup.name = MUON OR groups.leadingGroup.name = JETM )"
    )


def test_not_in_combined_with_or_needs_no_grouping() -> None:
    expr = parse_dsl(
        "status = Active OR status not in [Closed, Archived]", mode="analysis"
    )
    assert expr.to_dsl() == "status = Active OR status != Closed AND status != Archived"


def test_in_output_round_trips() -> None:
    src = "status != Closed AND groups.leadingGroup.name in [EGAM, MUON]"
    canonical = parse_dsl(src, mode="analysis").to_dsl()
    assert parse_dsl(canonical, mode="analysis").to_dsl() == canonical


def test_in_unknown_field_raises_validation_error() -> None:
    with pytest.raises(DSLValidationError, match="unknown field 'foo'"):
        parse_dsl("foo in [a, b]", mode="analysis")


def test_in_on_boolean_field_is_allowed() -> None:
    expr = parse_dsl('"analysisTeam.isContactEditor" in [true, false]', mode="analysis")
    assert expr.to_dsl() == (
        "analysisTeam.isContactEditor = true OR analysisTeam.isContactEditor = false"
    )


def test_in_empty_list_is_syntax_error() -> None:
    with pytest.raises(DSLSyntaxError):
        parse_dsl("status in []", mode="analysis")


def test_bare_value_with_comma_is_unchanged() -> None:
    expr = parse_dsl("shortTitle = a,b", mode="analysis")
    assert expr == Condition(field="shortTitle", operator=Operator.EQ, value="a,b")


@pytest.mark.parametrize(("keyword", "joiner"), [("in", " OR "), ("not in", " AND ")])
def test_list_longer_than_recursion_limit_serializes(keyword: str, joiner: str) -> None:
    """Expanded lists must not nest one level per item, or to_dsl() recursion
    overflows for long lists."""
    n = sys.getrecursionlimit() + 1
    items = ", ".join(f"v{i}" for i in range(n))
    dsl = parse_dsl(f"status {keyword} [{items}]", mode="analysis").to_dsl()
    assert dsl.count(joiner) == n - 1
    assert dsl.startswith("status ")
    assert dsl.endswith(f" v{n - 1}")

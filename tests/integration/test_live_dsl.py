"""Live integration tests for DSL grouping and list membership (``in`` / ``not in``).

Each test compares a query using the new syntax against an equivalent query
written out by hand, so no result counts are hard-coded. Skipped by default;
run with ``pixi run test-slow`` or ``pytest --runslow``.
"""

from __future__ import annotations

import functools
import json

import pytest
from typer.testing import CliRunner

from stare import Glance
from stare.cli import app
from stare.dsl.models import And, Condition, Expression, Operator, Or
from stare.settings import StareSettings

_LIVE_SETTINGS = StareSettings(cache_enabled=False)
_GROUP = "groups.leadingGroup.name"
_GROUPS = [
    "EGAM", "MUON", "JETM", "TAUP", "IDTR", "FTAG", "GPER", "STDM",
    "BPHY", "TOPQ", "HIGP", "HMBS", "EXOT", "HION", "PMGR",
]  # fmt: skip
# "not closed AND (EGAM OR MUON)", distributed by hand into the flat form the
# server evaluates correctly without parentheses.
_DISTRIBUTED = (
    f"status != Closed AND {_GROUP} = EGAM OR status != Closed AND {_GROUP} = MUON"
)

runner = CliRunner()


def _count(query: str | Expression, *, validate: bool = True) -> int:
    with Glance(settings=_LIVE_SETTINGS) as g:
        result = g.analyses.search(query=query, limit=1, validate_query=validate)
    assert result.number_of_results is not None
    return result.number_of_results


@pytest.mark.slow
class TestLiveListMembership:
    def test_in_under_and_matches_hand_distributed_query(self) -> None:
        """`in` under AND must mean AND-of-OR, i.e. the hand-distributed form."""
        expected = _count(_DISTRIBUTED, validate=False)
        assert expected > 0
        assert _count(f"status != Closed AND {_GROUP} in [EGAM, MUON]") == expected

    def test_fifteen_group_example_matches_reduce_or_of_and(self) -> None:
        """The motivating example from #81 against the hand-built reduce(Or) AST."""
        not_closed = Condition(field="status", operator=Operator.NE, value="Closed")
        branches: list[Expression] = [
            And(
                clauses=(
                    not_closed,
                    Condition(field=_GROUP, operator=Operator.EQ, value=grp),
                )
            )
            for grp in _GROUPS
        ]
        hand_built = functools.reduce(lambda a, b: Or(clauses=(a, b)), branches)
        expected = _count(hand_built)
        assert expected > 0
        assert (
            _count(f"status != Closed AND {_GROUP} in [{', '.join(_GROUPS)}]")
            == expected
        )

    def test_not_in_matches_hand_written_inequalities(self) -> None:
        expected = _count(f"{_GROUP} != EGAM AND {_GROUP} != MUON", validate=False)
        assert expected > 0
        assert _count(f"{_GROUP} not in [EGAM, MUON]") == expected

    def test_cli_accepts_in_query(self) -> None:
        query = f"status != Closed AND {_GROUP} in [EGAM, MUON]"
        result = runner.invoke(
            app,
            ["analysis", "search", "-q", query, "--limit", "1", "--json", "--no-cache"],
        )
        assert result.exit_code == 0, result.output
        assert json.loads(result.stdout)["numberOfResults"] == _count(query)


@pytest.mark.slow
class TestLiveParenthesizedGrouping:
    def test_parenthesized_dsl_matches_hand_distributed_query(self) -> None:
        """Parentheses in the DSL now change grouping instead of being dropped."""
        expected = _count(_DISTRIBUTED, validate=False)
        grouped = f"status != Closed AND ({_GROUP} = EGAM OR {_GROUP} = MUON)"
        assert _count(grouped) == expected

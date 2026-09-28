"""Every query and `get` in the docs, README, CLAUDE.md and CLI help must work live.

Complements ``tests/test_doc_examples.py``: that check only parses the queries,
so it cannot catch a *value* that does not exist on the server, such as a
made-up status (``status = Active``) or a raw status value the API no longer
matches (``status = phase1_closed``). Skipped by default; run with
``pixi run test-slow`` or ``pytest --runslow``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from stare import Glance
from stare.exceptions import NotFoundError
from stare.settings import StareSettings
from tests.test_doc_examples import _EXAMPLES, _GET_EXAMPLES

if TYPE_CHECKING:
    from collections.abc import Iterator

    from stare.typing import Mode

_LIVE_SETTINGS = StareSettings(cache_enabled=False)

# DSL mode -> Glance resource accessor
_ACCESSOR = {
    "analysis": "analyses",
    "paper": "papers",
    "confnote": "confnotes",
    "pubnote": "pubnotes",
    "plot": "plots",
    "publication": "publications",
    "leadinggroup": "leadinggroups",
    "subgroup": "subgroups",
    "trigger": "triggers",
}


@pytest.fixture(scope="module")
def glance() -> Iterator[Glance]:
    with Glance(settings=_LIVE_SETTINGS) as g:
        yield g


@pytest.mark.slow
@pytest.mark.parametrize(
    ("source", "mode", "query"), _EXAMPLES, ids=[f"{s}:{q}" for s, _, q in _EXAMPLES]
)
def test_documented_query_returns_results(
    glance: Glance, source: str, mode: Mode, query: str
) -> None:
    result = getattr(glance, _ACCESSOR[mode]).search(query=query, limit=1)
    assert result.number_of_results, f"{source}: {query!r} matches nothing"


@pytest.mark.slow
@pytest.mark.parametrize(
    ("source", "accessor", "ref_code"),
    _GET_EXAMPLES,
    ids=[f"{s}:{a}.get({r})" for s, a, r in _GET_EXAMPLES],
)
def test_documented_get_finds_record(
    glance: Glance, source: str, accessor: str, ref_code: str
) -> None:
    try:
        getattr(glance, accessor).get(ref_code)
    except NotFoundError:
        pytest.fail(f"{source}: {accessor}.get({ref_code!r}) finds nothing")

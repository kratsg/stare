"""Live integration tests against the real ATLAS Glance/Fence API.

Requires a valid CERN SSO session — run ``stare login`` first.

These tests are skipped by default. Run with::

    pixi run test-slow

or pass ``--runslow`` directly to pytest.
"""

from __future__ import annotations

import pytest

from stare import Glance
from stare.models import Analysis, SearchResult


@pytest.mark.slow
def test_search_analyses_returns_results() -> None:
    """GET /searchAnalysis returns a non-empty SearchResult."""
    with Glance() as g:
        result = g.analyses.search(limit=5)
    assert isinstance(result, SearchResult)
    assert result.total_rows is not None
    assert result.total_rows > 0
    assert len(result.results) > 0


@pytest.mark.slow
def test_search_analyses_by_reference_code() -> None:
    """Searching by referenceCode returns the expected analysis."""
    with Glance() as g:
        result = g.analyses.search(
            query='"referenceCode" = "ANA-HION-2018-01"', limit=1
        )
    assert result.total_rows is not None
    assert result.total_rows >= 1
    assert any(a.reference_code == "ANA-HION-2018-01" for a in result.results)


@pytest.mark.slow
def test_search_result_items_are_analysis_models() -> None:
    """All items in search results are valid Analysis instances."""
    with Glance() as g:
        result = g.analyses.search(limit=10)
    for item in result.results:
        assert isinstance(item, Analysis)
        assert item.reference_code is not None

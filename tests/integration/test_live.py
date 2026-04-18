"""Live integration tests against the real ATLAS Glance/Fence API.

Requires a valid CERN SSO session — run ``stare login`` first.

These tests are skipped by default. Run with::

    pixi run test-slow

or pass ``--runslow`` directly to pytest.
"""

from __future__ import annotations

from typing import Any

import pytest

from stare import Glance
from stare.dsl.registry import FieldRegistry
from stare.exceptions import StareError
from stare.models import Analysis, AnalysisSearchResult
from stare.settings import StareSettings

# Disable the on-disk HTTP cache for all live tests so results are always
# fetched fresh from the API rather than replayed from a stale SQLite entry.
_LIVE_SETTINGS = StareSettings(cache_enabled=False)

# Load field catalogues at collection time (no network needed).
_ANALYSIS_FIELDS = FieldRegistry.for_mode("analysis").fields()
_PAPER_FIELDS = FieldRegistry.for_mode("paper").fields()

_REFERENCE_ANALYSIS_CODE = "ANA-HION-2018-01"


def _get_nested_value(obj: dict[str, Any], path: str) -> str | None:
    """Extract a scalar string from a camelCase nested dict using a dot-path."""
    current: Any = obj
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
        if current is None:
            return None
    if isinstance(current, list):
        return str(current[0]) if current else None
    if isinstance(current, str):
        return current
    return None


@pytest.fixture(scope="session")
def reference_analysis() -> Analysis:
    try:
        with Glance(settings=_LIVE_SETTINGS) as g:
            result = g.analyses.search(
                query=f"referenceCode = {_REFERENCE_ANALYSIS_CODE}", limit=1
            )
    except StareError as exc:
        pytest.skip(f"Live API unavailable: {exc}")
    assert result.total_rows is not None
    assert result.total_rows >= 1
    match = next(
        (a for a in result.results if a.reference_code == _REFERENCE_ANALYSIS_CODE),
        None,
    )
    assert match is not None, f"{_REFERENCE_ANALYSIS_CODE} not in results"
    return match


@pytest.mark.slow
def test_search_analyses_returns_results() -> None:
    """GET /searchAnalysis returns a non-empty AnalysisSearchResult."""
    with Glance(settings=_LIVE_SETTINGS) as g:
        result = g.analyses.search(limit=5)
    assert isinstance(result, AnalysisSearchResult)
    assert result.total_rows is not None
    assert result.total_rows > 0
    assert len(result.results) > 0


@pytest.mark.slow
def test_search_analyses_by_reference_code() -> None:
    """Searching by referenceCode returns the expected analysis."""
    with Glance(settings=_LIVE_SETTINGS) as g:
        result = g.analyses.search(
            query=f"referenceCode = {_REFERENCE_ANALYSIS_CODE}", limit=1
        )
    assert result.total_rows is not None
    assert result.total_rows >= 1
    assert any(a.reference_code == _REFERENCE_ANALYSIS_CODE for a in result.results)


@pytest.mark.slow
def test_search_result_items_are_analysis_models() -> None:
    """All items in search results are valid Analysis instances."""
    with Glance(settings=_LIVE_SETTINGS) as g:
        result = g.analyses.search(limit=10)
    for item in result.results:
        assert isinstance(item, Analysis)
        assert item.reference_code is not None


@pytest.mark.slow
@pytest.mark.parametrize("field", _ANALYSIS_FIELDS)
def test_analysis_field_is_searchable(field: str, reference_analysis: Analysis) -> None:
    """Each catalogue field can be used in a live query without a server error."""
    record = reference_analysis.model_dump(by_alias=True)
    value = _get_nested_value(record, field)
    if value is None:
        pytest.skip(f"field '{field}' has no value in reference record")
    if " " in value:
        pytest.skip(
            f"field '{field}' value contains spaces — not expressible in bare-value DSL"
        )

    with Glance(settings=_LIVE_SETTINGS) as g:
        result = g.analyses.search(
            query=f"{field} = {value}",
            limit=1,
            validate_query=False,
        )
    assert result.total_rows is not None
    assert result.total_rows >= 1

"""Live integration tests against the real ATLAS Glance/Fence API.

Requires a valid CERN SSO session — run ``stare login`` first.

These tests are skipped by default. Run with::

    pixi run test-slow

or pass ``--runslow`` directly to pytest.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, NamedTuple

import pytest

from stare import Glance
from stare.dsl.models import Condition, Operator
from stare.dsl.registry import FieldRegistry
from stare.exceptions import StareError
from stare.models import Analysis, AnalysisSearchResult, ConfNote, Paper, Plot, PubNote
from stare.models.search import (
    ConfNoteSearchResult,
    PaperSearchResult,
    PlotSearchResult,
    PubNoteSearchResult,
)
from stare.settings import StareSettings

if TYPE_CHECKING:
    from pydantic import BaseModel

# Disable the on-disk HTTP cache for all live tests so results are always
# fetched fresh from the API rather than replayed from a stale SQLite entry.
_LIVE_SETTINGS = StareSettings(cache_enabled=False)

# Load field catalogues at collection time (no network needed).
_ANALYSIS_FIELDS = FieldRegistry.for_mode("analysis").fields()
_PAPER_FIELDS = FieldRegistry.for_mode("paper").fields()
_CONFNOTE_FIELDS = FieldRegistry.for_mode("confnote").fields()
_PUBNOTE_FIELDS = FieldRegistry.for_mode("pubnote").fields()
_PLOT_FIELDS = FieldRegistry.for_mode("plot").fields()

_REFERENCE_ANALYSIS_CODE = "ANA-HION-2018-01"
_REFERENCE_PAPER_CODE = "IDET-2010-01"
_REFERENCE_CONFNOTE_FINAL_CODE = "ATLAS-CONF-2018-011"
# No final ATL-PHYS-PUB code is assigned to this note, so it is matched on its
# temporary reference code.
_REFERENCE_PUBNOTE_TEMP_CODE = "PUB-HIGP-2024-59"
_REFERENCE_PLOT_CODE = "PLOT-MUON-2018-08"


class _DateOnlyFilterError(Exception):
    """A date filter with the returned datetime matched nothing (ATGLANCE-8334)."""


class _FieldValue(NamedTuple):
    """A field's value in a reference record, and whether it sits in a list."""

    value: str
    in_list: bool


def _get_nested_value(record: BaseModel, path: str) -> _FieldValue | None:
    """Extract a scalar string from a record using a camelCase dot-path.

    The record is dumped in JSON mode so dates and datetimes come back as the
    strings the API returns. A list anywhere along the path resolves through
    its first element, matching how the field catalogue names list items
    (``phase0.eoiMeetings.date``, ``metadata.keywords.name``).
    """
    current: Any = record.model_dump(by_alias=True, mode="json")
    in_list = False
    for part in path.split("."):
        if isinstance(current, list):
            in_list = True
            current = current[0] if current else None
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    if isinstance(current, list):
        in_list = True
        current = current[0] if current else None
    if isinstance(current, str):
        return _FieldValue(current, in_list=in_list)
    return None


_ISO_DATETIME = re.compile(r"^\d{4}-\d{2}-\d{2}T")
_ATGLANCE_8334 = "https://its.cern.ch/jira/browse/ATGLANCE-8334"


def _field_query(field: str, found: _FieldValue | None) -> str:
    """Build the query for a live field-searchability test.

    Fields inside a list are queried with ``contain``: on the server, ``=``
    only matches a record whose list holds that value as its sole element,
    so ``metadata.keywords.name = "5.02 TeV"`` misses a record that has the
    keyword among several. Everything else uses ``=``.

    Date filters match ``YYYY-MM-DD`` only, although the API returns ISO
    datetimes, so datetime values are truncated to their date
    (ATGLANCE-8334, see ``test_date_filter_matches_returned_datetime``).
    """
    if found is None:
        pytest.skip(f"field '{field}' has no value in reference record")
    value = found.value
    if _ISO_DATETIME.match(value):
        value = value[:10]
    try:
        operator = Operator.CONTAIN if found.in_list else Operator.EQ
        return Condition(field=field, operator=operator, value=value).to_dsl()
    except ValueError as exc:
        pytest.skip(str(exc))


# ---------------------------------------------------------------------------
# Analysis fixtures and tests
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def reference_analysis() -> Analysis:
    try:
        with Glance(settings=_LIVE_SETTINGS) as g:
            result = g.analyses.search(
                query=f"referenceCode = {_REFERENCE_ANALYSIS_CODE}", limit=1
            )
    except StareError as exc:
        pytest.skip(f"Live API unavailable: {exc}")
    assert result.number_of_results is not None
    assert result.number_of_results >= 1
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
    assert result.number_of_results is not None
    assert result.number_of_results > 0
    assert len(result.results) > 0


@pytest.mark.slow
def test_search_analyses_by_reference_code() -> None:
    """Searching by referenceCode returns the expected analysis."""
    with Glance(settings=_LIVE_SETTINGS) as g:
        result = g.analyses.search(
            query=f"referenceCode = {_REFERENCE_ANALYSIS_CODE}", limit=1
        )
    assert result.number_of_results is not None
    assert result.number_of_results >= 1
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
    found = _get_nested_value(reference_analysis, field)
    query = _field_query(field, found)

    with Glance(settings=_LIVE_SETTINGS) as g:
        result = g.analyses.search(
            query=query,
            limit=1,
            validate_query=False,
        )
    assert result.number_of_results is not None
    assert result.number_of_results >= 1


@pytest.mark.slow
@pytest.mark.xfail(
    raises=_DateOnlyFilterError,
    reason=f"date filters match YYYY-MM-DD only: {_ATGLANCE_8334}",
    strict=True,
)
def test_date_filter_matches_returned_datetime(reference_analysis: Analysis) -> None:
    """Filtering on a date field with the datetime the API returns should match.

    Strict, so a server fix shows up as XPASS(strict): then drop this marker
    and the datetime truncation in ``_field_query()``.
    """
    field = "phase0.eoiMeetings.date"
    found = _get_nested_value(reference_analysis, field)
    assert found is not None
    value = found.value
    assert _ISO_DATETIME.match(value), value
    query = Condition(field=field, operator=Operator.EQ, value=value).to_dsl()

    with Glance(settings=_LIVE_SETTINGS) as g:
        result = g.analyses.search(query=query, limit=1, validate_query=False)
    assert result.number_of_results is not None
    # Only a zero-result response is the known bug; anything else must fail.
    if result.number_of_results == 0:
        raise _DateOnlyFilterError(query)


# ---------------------------------------------------------------------------
# Paper fixtures and tests
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def reference_paper() -> Paper:
    try:
        with Glance(settings=_LIVE_SETTINGS) as g:
            result = g.papers.search(
                query=f"referenceCode = {_REFERENCE_PAPER_CODE}", limit=1
            )
    except StareError as exc:
        pytest.skip(f"Live API unavailable: {exc}")
    assert result.number_of_results is not None
    assert result.number_of_results >= 1
    match = next(
        (p for p in result.results if p.reference_code == _REFERENCE_PAPER_CODE),
        None,
    )
    assert match is not None, f"{_REFERENCE_PAPER_CODE} not in results"
    return match


@pytest.mark.slow
def test_search_papers_returns_results() -> None:
    """GET /searchPaper returns a non-empty PaperSearchResult."""
    with Glance(settings=_LIVE_SETTINGS) as g:
        result = g.papers.search(limit=5)
    assert isinstance(result, PaperSearchResult)
    assert result.number_of_results is not None
    assert result.number_of_results > 0
    assert len(result.results) > 0


@pytest.mark.slow
def test_search_papers_by_reference_code() -> None:
    """Searching by referenceCode returns the expected paper."""
    with Glance(settings=_LIVE_SETTINGS) as g:
        result = g.papers.search(
            query=f"referenceCode = {_REFERENCE_PAPER_CODE}", limit=1
        )
    assert result.number_of_results is not None
    assert result.number_of_results >= 1
    assert any(p.reference_code == _REFERENCE_PAPER_CODE for p in result.results)


@pytest.mark.slow
def test_search_result_items_are_paper_models() -> None:
    """All items in search results are valid Paper instances."""
    with Glance(settings=_LIVE_SETTINGS) as g:
        result = g.papers.search(limit=10)
    for item in result.results:
        assert isinstance(item, Paper)
        assert item.reference_code is not None


@pytest.mark.slow
@pytest.mark.parametrize("field", _PAPER_FIELDS)
def test_paper_field_is_searchable(field: str, reference_paper: Paper) -> None:
    """Each catalogue field can be used in a live query without a server error."""
    found = _get_nested_value(reference_paper, field)
    query = _field_query(field, found)

    with Glance(settings=_LIVE_SETTINGS) as g:
        result = g.papers.search(
            query=query,
            limit=1,
            validate_query=False,
        )
    assert result.number_of_results is not None
    assert result.number_of_results >= 1


# ---------------------------------------------------------------------------
# ConfNote fixtures and tests
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def reference_confnote() -> ConfNote:
    try:
        with Glance(settings=_LIVE_SETTINGS) as g:
            result = g.confnotes.search(
                query=f"finalReferenceCode = {_REFERENCE_CONFNOTE_FINAL_CODE}", limit=1
            )
    except StareError as exc:
        pytest.skip(f"Live API unavailable: {exc}")
    assert result.number_of_results is not None
    assert result.number_of_results >= 1
    match = next(
        (
            c
            for c in result.results
            if c.final_reference_code == _REFERENCE_CONFNOTE_FINAL_CODE
        ),
        None,
    )
    assert match is not None, f"{_REFERENCE_CONFNOTE_FINAL_CODE} not in results"
    return match


@pytest.mark.slow
def test_search_confnotes_returns_results() -> None:
    """GET /searchConfnote returns a non-empty ConfNoteSearchResult."""
    with Glance(settings=_LIVE_SETTINGS) as g:
        result = g.confnotes.search(limit=5)
    assert isinstance(result, ConfNoteSearchResult)
    assert result.number_of_results is not None
    assert result.number_of_results > 0
    assert len(result.results) > 0


@pytest.mark.slow
def test_search_confnotes_by_final_reference_code() -> None:
    """Searching by finalReferenceCode returns the expected CONF note."""
    with Glance(settings=_LIVE_SETTINGS) as g:
        result = g.confnotes.search(
            query=f"finalReferenceCode = {_REFERENCE_CONFNOTE_FINAL_CODE}", limit=1
        )
    assert result.number_of_results is not None
    assert result.number_of_results >= 1
    assert any(
        c.final_reference_code == _REFERENCE_CONFNOTE_FINAL_CODE for c in result.results
    )


@pytest.mark.slow
def test_search_result_items_are_confnote_models() -> None:
    """All items in search results are valid ConfNote instances."""
    with Glance(settings=_LIVE_SETTINGS) as g:
        result = g.confnotes.search(limit=10)
    for item in result.results:
        assert isinstance(item, ConfNote)


@pytest.mark.slow
@pytest.mark.parametrize("field", _CONFNOTE_FIELDS)
def test_confnote_field_is_searchable(field: str, reference_confnote: ConfNote) -> None:
    """Each catalogue field can be used in a live query without a server error."""
    found = _get_nested_value(reference_confnote, field)
    query = _field_query(field, found)

    with Glance(settings=_LIVE_SETTINGS) as g:
        result = g.confnotes.search(
            query=query,
            limit=1,
            validate_query=False,
        )
    assert result.number_of_results is not None
    assert result.number_of_results >= 1


# ---------------------------------------------------------------------------
# PubNote fixtures and tests
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def reference_pubnote() -> PubNote:
    try:
        with Glance(settings=_LIVE_SETTINGS) as g:
            result = g.pubnotes.search(
                query=f"temporaryReferenceCode = {_REFERENCE_PUBNOTE_TEMP_CODE}",
                limit=1,
            )
    except StareError as exc:
        pytest.skip(f"Live API unavailable: {exc}")
    assert result.number_of_results is not None
    assert result.number_of_results >= 1
    match = next(
        (
            p
            for p in result.results
            if p.temp_reference_code == _REFERENCE_PUBNOTE_TEMP_CODE
        ),
        None,
    )
    assert match is not None, f"{_REFERENCE_PUBNOTE_TEMP_CODE} not in results"
    return match


@pytest.mark.slow
def test_search_pubnotes_returns_results() -> None:
    """GET /searchPubnote returns a non-empty PubNoteSearchResult."""
    with Glance(settings=_LIVE_SETTINGS) as g:
        result = g.pubnotes.search(limit=5)
    assert isinstance(result, PubNoteSearchResult)
    assert result.number_of_results is not None
    assert result.number_of_results > 0
    assert len(result.results) > 0


@pytest.mark.slow
def test_search_pubnotes_by_temporary_reference_code() -> None:
    """Searching by temporaryReferenceCode returns the expected PUB note."""
    with Glance(settings=_LIVE_SETTINGS) as g:
        result = g.pubnotes.search(
            query=f"temporaryReferenceCode = {_REFERENCE_PUBNOTE_TEMP_CODE}", limit=1
        )
    assert result.number_of_results is not None
    assert result.number_of_results >= 1
    assert any(
        p.temp_reference_code == _REFERENCE_PUBNOTE_TEMP_CODE for p in result.results
    )


@pytest.mark.slow
def test_search_result_items_are_pubnote_models() -> None:
    """All items in search results are valid PubNote instances."""
    with Glance(settings=_LIVE_SETTINGS) as g:
        result = g.pubnotes.search(limit=10)
    for item in result.results:
        assert isinstance(item, PubNote)


@pytest.mark.slow
@pytest.mark.parametrize("field", _PUBNOTE_FIELDS)
def test_pubnote_field_is_searchable(field: str, reference_pubnote: PubNote) -> None:
    """Each catalogue field can be used in a live query without a server error."""
    found = _get_nested_value(reference_pubnote, field)
    query = _field_query(field, found)

    with Glance(settings=_LIVE_SETTINGS) as g:
        result = g.pubnotes.search(
            query=query,
            limit=1,
            validate_query=False,
        )
    assert result.number_of_results is not None
    assert result.number_of_results >= 1


# ---------------------------------------------------------------------------
# Plot fixtures and tests
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def reference_plot() -> Plot:
    try:
        with Glance(settings=_LIVE_SETTINGS) as g:
            result = g.plots.search(
                query=f"referenceCode = {_REFERENCE_PLOT_CODE}", limit=1
            )
    except StareError as exc:
        pytest.skip(f"Live API unavailable: {exc}")
    assert result.number_of_results is not None
    assert result.number_of_results >= 1
    match = next(
        (p for p in result.results if p.reference_code == _REFERENCE_PLOT_CODE),
        None,
    )
    assert match is not None, f"{_REFERENCE_PLOT_CODE} not in results"
    return match


@pytest.mark.slow
def test_search_plots_returns_results() -> None:
    """GET /searchPlot returns a non-empty PlotSearchResult."""
    with Glance(settings=_LIVE_SETTINGS) as g:
        result = g.plots.search(limit=5)
    assert isinstance(result, PlotSearchResult)
    assert result.number_of_results is not None
    assert result.number_of_results > 0
    assert len(result.results) > 0


@pytest.mark.slow
def test_search_plots_by_reference_code() -> None:
    """Searching by referenceCode returns the expected plot."""
    with Glance(settings=_LIVE_SETTINGS) as g:
        result = g.plots.search(
            query=f"referenceCode = {_REFERENCE_PLOT_CODE}", limit=1
        )
    assert result.number_of_results is not None
    assert result.number_of_results >= 1
    assert any(p.reference_code == _REFERENCE_PLOT_CODE for p in result.results)


@pytest.mark.slow
def test_search_result_items_are_plot_models() -> None:
    """All items in search results are valid Plot instances."""
    with Glance(settings=_LIVE_SETTINGS) as g:
        result = g.plots.search(limit=10)
    for item in result.results:
        assert isinstance(item, Plot)
        assert item.reference_code is not None


@pytest.mark.slow
@pytest.mark.parametrize("field", _PLOT_FIELDS)
def test_plot_field_is_searchable(field: str, reference_plot: Plot) -> None:
    """Each catalogue field can be used in a live query without a server error."""
    found = _get_nested_value(reference_plot, field)
    query = _field_query(field, found)

    with Glance(settings=_LIVE_SETTINGS) as g:
        result = g.plots.search(
            query=query,
            limit=1,
            validate_query=False,
        )
    assert result.number_of_results is not None
    assert result.number_of_results >= 1

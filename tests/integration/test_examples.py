"""Integration tests that exercise the code examples shown in docs/examples.md.

Each test is a close translation of one documented example. They run against
the live ATLAS Glance API and are skipped by default.

Run with::

    pixi run test-slow

or::

    pytest --runslow tests/integration/test_examples.py

Requires a valid CERN SSO session (``stare auth login``).
``STARE_EXCHANGE_AUDIENCE`` defaults to the production audience and does not
need to be set explicitly.
"""

from __future__ import annotations

import pytest

from stare import Glance
from stare.exceptions import AuthenticationError, StareError
from stare.models import Analysis, Paper
from stare.models.enums import MeetingType
from stare.settings import StareSettings

_LIVE = StareSettings(cache_enabled=False)
_REF_ANALYSIS = "ANA-HION-2018-01"
_REF_PAPER = "EXOT-2018-14"


@pytest.fixture(scope="session")
def glance() -> Glance:
    """Session-scoped Glance client."""
    return Glance(settings=_LIVE)


# ---------------------------------------------------------------------------
# Analysis examples
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_search_analyses(glance: Glance) -> None:
    """docs/examples.md — Search analyses."""
    result = glance.analyses.search()
    assert result.number_of_results is not None
    assert result.number_of_results > 0
    for analysis in result.results:
        assert isinstance(analysis, Analysis)


@pytest.mark.slow
def test_filter_with_dsl(glance: Glance) -> None:
    """docs/examples.md — Filter with the DSL."""
    result = glance.analyses.search(
        query="groups.leadingGroup = HIGG",
        limit=10,
        sort_by="creationDate",
        sort_desc=True,
    )
    assert result.number_of_results is not None
    assert result.number_of_results > 0
    for analysis in result.results:
        assert analysis.groups is not None
        assert analysis.groups.leading_group == "HIGG"


@pytest.mark.slow
def test_look_up_specific_analysis(glance: Glance) -> None:
    """docs/examples.md — Look up a specific analysis."""
    result = glance.analyses.search(query=f"referenceCode = {_REF_ANALYSIS}", limit=1)
    assert len(result.results) == 1
    analysis = result.results[0]
    assert analysis.reference_code == _REF_ANALYSIS
    assert analysis.groups is not None
    assert analysis.groups.leading_group is not None


@pytest.mark.slow
def test_inspect_analysis_team(glance: Glance) -> None:
    """docs/examples.md — Inspect the analysis team."""
    result = glance.analyses.search(query=f"referenceCode = {_REF_ANALYSIS}", limit=1)
    analysis = result.results[0]
    editors = [m for m in analysis.analysis_team if m.is_contact_editor]
    assert len(editors) >= 1
    for editor in editors:
        assert isinstance(editor.is_contact_editor, bool)
        assert editor.cern_ccid is not None


@pytest.mark.slow
def test_inspect_phase0_meetings(glance: Glance) -> None:
    """docs/examples.md — Inspect phase 0 meetings."""
    result = glance.analyses.search(query=f"referenceCode = {_REF_ANALYSIS}", limit=1)
    analysis = result.results[0]
    assert analysis.phase0 is not None
    assert len(analysis.phase0.meetings) > 0
    for meeting in analysis.phase0.meetings:
        assert MeetingType(meeting.meeting_type) in list(MeetingType)
        if meeting.link is not None:
            assert meeting.link.url is not None


# ---------------------------------------------------------------------------
# Paper examples
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_search_papers(glance: Glance) -> None:
    """docs/examples.md — Search papers."""
    result = glance.papers.search(query="groups.leadingGroup = HDBS", limit=10)
    assert result.number_of_results is not None
    assert result.number_of_results > 0
    for paper in result.results:
        assert isinstance(paper, Paper)


@pytest.mark.slow
def test_paper_submission_data(glance: Glance) -> None:
    """docs/examples.md — Access paper submission data."""
    result = glance.papers.search(query=f"referenceCode = {_REF_PAPER}", limit=1)
    assert len(result.results) == 1
    paper = result.results[0]
    assert paper.submission is not None
    assert len(paper.submission.arxiv_urls) >= 1
    for link in paper.submission.arxiv_urls:
        assert link.url is not None
    assert isinstance(paper.submission.physics_briefings, list)
    assert isinstance(paper.submission.final_journal_publications, list)
    assert len(paper.submission.final_journal_publications) >= 1


# ---------------------------------------------------------------------------
# Pagination example
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_paginate_through_results(glance: Glance) -> None:
    """docs/examples.md — Paginate through all results."""
    limit = 10
    offset = 0
    all_codes: list[str] = []

    while True:
        result = glance.analyses.search(
            query="groups.leadingGroup = HIGG",
            limit=limit,
            offset=offset,
        )
        all_codes.extend(a.reference_code for a in result.results if a.reference_code)
        offset += len(result.results)
        if offset >= (result.number_of_results or 0):
            break
        if offset >= 30:  # cap at 3 pages to keep the test fast
            break

    assert len(all_codes) > 0


# ---------------------------------------------------------------------------
# Cache / context manager / error handling examples
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_disable_cache() -> None:
    """docs/examples.md — Disable the cache (uses its own Glance instance)."""
    g = Glance(settings=StareSettings(cache_enabled=False))
    result = g.analyses.search(limit=5)
    assert result.number_of_results is not None
    assert result.number_of_results > 0


@pytest.mark.slow
def test_context_manager() -> None:
    """docs/examples.md — Use as a context manager."""
    with Glance(settings=_LIVE) as g:
        analyses = g.analyses.search(limit=5)
        papers = g.papers.search(limit=5)
    assert len(analyses.results) > 0
    assert len(papers.results) > 0


@pytest.mark.slow
def test_error_handling_auth_error_type() -> None:
    """docs/examples.md — AuthenticationError is a subclass of StareError."""
    assert issubclass(AuthenticationError, StareError)

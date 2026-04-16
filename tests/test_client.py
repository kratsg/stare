"""Tests for stare.client (Glance + resource accessors)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest
import respx

from stare.client import Glance
from stare.exceptions import ApiError, ForbiddenError, NotFoundError, UnauthorizedError
from stare.models import (
    Analysis,
    ConfNote,
    Paper,
    PublicationRef,
    PubNote,
    SearchResult,
    Trigger,
)

if TYPE_CHECKING:
    from stare.settings import StareSettings

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_BASE = "https://test-glance.example.com/api"

SAMPLE_ANALYSIS = {
    "referenceCode": "ANA-TEST-2024-01",
    "status": "Active",
    "shortTitle": "Test analysis",
    "publicShortTitle": "Public test",
    "groups": {"leadingGroup": ["HDBS"], "subgroups": [], "otherGroups": []},
    "phase0": {"state": "Approved"},
}

SAMPLE_SEARCH = {
    "totalRows": 1,
    "results": [SAMPLE_ANALYSIS],
}

SAMPLE_PAPER = {
    "referenceCode": "HDBS-2024-01",
    "status": "Published",
    "shortTitle": "Test paper",
}

SAMPLE_CONF_NOTE = {
    "temporaryReferenceCode": "ATLAS-CONF-2024-001",
    "status": "Active",
    "shortTitle": "Test conf note",
}

SAMPLE_PUB_NOTE = {
    "temporaryReferenceCode": "ATL-PHYS-PUB-2024-001",
    "status": "Active",
    "shortTitle": "Test pub note",
}

SAMPLE_ERROR = {"status": 404, "title": "Not Found", "detail": "Resource not found"}

SAMPLE_PUBLICATIONS = [
    {"referenceCode": "HDBS-2024-01", "type": "Paper"},
    {"referenceCode": "ATLAS-CONF-2024-001", "type": "ConfNote"},
]

SAMPLE_TRIGGERS = [
    {"name": "HLT_e60_lhmedium", "category": {"name": "electron", "year": "2024"}},
]


@pytest.fixture
def glance(test_settings: StareSettings) -> Glance:
    """Glance instance using a fixed token (no real auth)."""
    return Glance(settings=test_settings, token="fake-token")


# ---------------------------------------------------------------------------
# Glance constructor and context manager
# ---------------------------------------------------------------------------


def test_glance_uses_token_directly(test_settings: StareSettings) -> None:
    g = Glance(settings=test_settings, token="my-token")
    assert g._token == "my-token"


def test_glance_context_manager(test_settings: StareSettings) -> None:
    with Glance(settings=test_settings, token="tok") as g:
        assert g is not None


def test_glance_injects_auth_header(test_settings: StareSettings) -> None:
    with respx.mock(base_url=_BASE) as rx:
        rx.get("/searchAnalysis").mock(
            return_value=httpx.Response(200, json=SAMPLE_SEARCH)
        )
        with Glance(settings=test_settings, token="bearer-token") as g:
            g.analyses.search()
        assert rx.calls[0].request.headers["Authorization"] == "Bearer bearer-token"


# ---------------------------------------------------------------------------
# AnalysisResource.search
# ---------------------------------------------------------------------------


def test_analyses_search_returns_search_result(glance: Glance) -> None:
    with respx.mock(base_url=_BASE) as rx:
        rx.get("/searchAnalysis").mock(
            return_value=httpx.Response(200, json=SAMPLE_SEARCH)
        )
        result = glance.analyses.search()

    assert isinstance(result, SearchResult)
    assert result.total_rows == 1
    assert len(result.results) == 1
    assert isinstance(result.results[0], Analysis)
    assert result.results[0].reference_code == "ANA-TEST-2024-01"


def test_analyses_search_passes_query_params(glance: Glance) -> None:
    with respx.mock(base_url=_BASE) as rx:
        rx.get("/searchAnalysis").mock(
            return_value=httpx.Response(200, json={"totalRows": 0, "results": []})
        )
        glance.analyses.search(query='"referenceCode" = "X"', limit=10, offset=5)
        params = dict(rx.calls[0].request.url.params)
    assert params["query"] == '"referenceCode" = "X"'
    assert params["limit"] == "10"
    assert params["offset"] == "5"


def test_analyses_search_sort_params(glance: Glance) -> None:
    with respx.mock(base_url=_BASE) as rx:
        rx.get("/searchAnalysis").mock(
            return_value=httpx.Response(200, json={"totalRows": 0, "results": []})
        )
        glance.analyses.search(sort_by="referenceCode", sort_desc=True)
        params = dict(rx.calls[0].request.url.params)
    assert params["sortBy"] == "referenceCode"
    assert params["sortDesc"] == "true"


def test_analyses_search_omits_none_params(glance: Glance) -> None:
    with respx.mock(base_url=_BASE) as rx:
        rx.get("/searchAnalysis").mock(
            return_value=httpx.Response(200, json={"totalRows": 0, "results": []})
        )
        glance.analyses.search()  # no query, no sort
        params = dict(rx.calls[0].request.url.params)
    assert "query" not in params
    assert "sortBy" not in params
    assert "sortDesc" not in params


# ---------------------------------------------------------------------------
# AnalysisResource.get
# ---------------------------------------------------------------------------


def test_analyses_get_returns_analysis(glance: Glance) -> None:
    with respx.mock(base_url=_BASE) as rx:
        rx.get("/analyses/ANA-TEST-2024-01").mock(
            return_value=httpx.Response(200, json=SAMPLE_ANALYSIS)
        )
        result = glance.analyses.get("ANA-TEST-2024-01")

    assert isinstance(result, Analysis)
    assert result.reference_code == "ANA-TEST-2024-01"


def test_analyses_get_404_raises_not_found(glance: Glance) -> None:
    with respx.mock(base_url=_BASE) as rx:
        rx.get("/analyses/MISSING").mock(
            return_value=httpx.Response(404, json=SAMPLE_ERROR)
        )
        with pytest.raises(NotFoundError):
            glance.analyses.get("MISSING")


# ---------------------------------------------------------------------------
# PaperResource.get
# ---------------------------------------------------------------------------


def test_papers_get_returns_paper(glance: Glance) -> None:
    with respx.mock(base_url=_BASE) as rx:
        rx.get("/papers/HDBS-2024-01").mock(
            return_value=httpx.Response(200, json=SAMPLE_PAPER)
        )
        result = glance.papers.get("HDBS-2024-01")

    assert isinstance(result, Paper)
    assert result.reference_code == "HDBS-2024-01"


def test_papers_get_401_raises_unauthorized(glance: Glance) -> None:
    err = {"status": 401, "title": "Unauthorized", "detail": "Missing token"}
    with respx.mock(base_url=_BASE) as rx:
        rx.get("/papers/X").mock(return_value=httpx.Response(401, json=err))
        with pytest.raises(UnauthorizedError):
            glance.papers.get("X")


def test_papers_get_403_raises_forbidden(glance: Glance) -> None:
    err = {"status": 403, "title": "Forbidden", "detail": "Access denied"}
    with respx.mock(base_url=_BASE) as rx:
        rx.get("/papers/X").mock(return_value=httpx.Response(403, json=err))
        with pytest.raises(ForbiddenError):
            glance.papers.get("X")


# ---------------------------------------------------------------------------
# ConfNoteResource.get
# ---------------------------------------------------------------------------


def test_conf_notes_get_returns_conf_note(glance: Glance) -> None:
    with respx.mock(base_url=_BASE) as rx:
        rx.get("/confnotes/ATLAS-CONF-2024-001").mock(
            return_value=httpx.Response(200, json=SAMPLE_CONF_NOTE)
        )
        result = glance.conf_notes.get("ATLAS-CONF-2024-001")

    assert isinstance(result, ConfNote)
    assert result.temp_reference_code == "ATLAS-CONF-2024-001"


# ---------------------------------------------------------------------------
# PubNoteResource.get
# ---------------------------------------------------------------------------


def test_pub_notes_get_returns_pub_note(glance: Glance) -> None:
    with respx.mock(base_url=_BASE) as rx:
        rx.get("/pubnotes/ATL-PHYS-PUB-2024-001").mock(
            return_value=httpx.Response(200, json=SAMPLE_PUB_NOTE)
        )
        result = glance.pub_notes.get("ATL-PHYS-PUB-2024-001")

    assert isinstance(result, PubNote)
    assert result.temp_reference_code == "ATL-PHYS-PUB-2024-001"


# ---------------------------------------------------------------------------
# PublicationResource.search
# ---------------------------------------------------------------------------


def test_publications_search_returns_list(glance: Glance) -> None:
    with respx.mock(base_url=_BASE) as rx:
        rx.get("/publications/search").mock(
            return_value=httpx.Response(200, json=SAMPLE_PUBLICATIONS)
        )
        result = glance.publications.search()

    assert isinstance(result, list)
    assert len(result) == 2
    assert isinstance(result[0], PublicationRef)
    assert result[0].reference_code == "HDBS-2024-01"


def test_publications_search_passes_filter_params(glance: Glance) -> None:
    with respx.mock(base_url=_BASE) as rx:
        rx.get("/publications/search").mock(return_value=httpx.Response(200, json=[]))
        glance.publications.search(types=["Paper"], leading_groups=["HDBS"])
        params = rx.calls[0].request.url.params
    assert "Paper" in params.get_list("types")
    assert "HDBS" in params.get_list("leadingGroups")


# ---------------------------------------------------------------------------
# GroupResource.list
# ---------------------------------------------------------------------------


def test_groups_list_returns_strings(glance: Glance) -> None:
    with respx.mock(base_url=_BASE) as rx:
        rx.get("/groups").mock(
            return_value=httpx.Response(200, json=["HDBS", "SUSY", "EXOT"])
        )
        result = glance.groups.list()

    assert result == ["HDBS", "SUSY", "EXOT"]


# ---------------------------------------------------------------------------
# SubgroupResource.list
# ---------------------------------------------------------------------------


def test_subgroups_list_returns_strings(glance: Glance) -> None:
    with respx.mock(base_url=_BASE) as rx:
        rx.get("/subgroups").mock(
            return_value=httpx.Response(200, json=["Higgs", "Dibosons"])
        )
        result = glance.subgroups.list()

    assert result == ["Higgs", "Dibosons"]


# ---------------------------------------------------------------------------
# TriggerResource.search
# ---------------------------------------------------------------------------


def test_triggers_search_returns_triggers(glance: Glance) -> None:
    with respx.mock(base_url=_BASE) as rx:
        rx.get("/triggers/search").mock(
            return_value=httpx.Response(200, json=SAMPLE_TRIGGERS)
        )
        result = glance.triggers.search()

    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], Trigger)
    assert result[0].name == "HLT_e60_lhmedium"
    assert result[0].category is not None
    assert result[0].category.name == "electron"


def test_triggers_search_passes_filter_params(glance: Glance) -> None:
    with respx.mock(base_url=_BASE) as rx:
        rx.get("/triggers/search").mock(return_value=httpx.Response(200, json=[]))
        glance.triggers.search(categories=["electron"], years=["2024"])
        params = rx.calls[0].request.url.params
    assert "electron" in params.get_list("categories")
    assert "2024" in params.get_list("years")


# ---------------------------------------------------------------------------
# Generic error handling
# ---------------------------------------------------------------------------


def test_generic_api_error_on_500(glance: Glance) -> None:
    err = {"status": 500, "title": "Internal Server Error", "detail": "Oops"}
    with respx.mock(base_url=_BASE) as rx:
        rx.get("/groups").mock(return_value=httpx.Response(500, json=err))
        with pytest.raises(ApiError) as exc_info:
            glance.groups.list()
    assert exc_info.value.status_code == 500

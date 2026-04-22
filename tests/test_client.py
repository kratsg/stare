"""Tests for stare.client (Glance + resource accessors)."""

from __future__ import annotations

from importlib.resources import as_file, files
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import httpx
import pytest
import respx
from pydantic import BaseModel as PydanticBase
from pydantic import ValidationError

from stare.client import Glance
from stare.dsl import DSLValidationError
from stare.dsl.models import Condition, Operator
from stare.exceptions import (
    ApiError,
    ForbiddenError,
    NotFoundError,
    ResponseParseError,
    StareError,
    UnauthorizedError,
)
from stare.models import (
    Analysis,
    AnalysisSearchResult,
    ConfNote,
    Paper,
    PaperSearchResult,
    PublicationRef,
    PubNote,
    Trigger,
)
from stare.models.common import _format_parse_error

if TYPE_CHECKING:
    from stare.settings import StareSettings

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_BASE = "https://test-glance.example.com/api"

SAMPLE_ANALYSIS = {
    "referenceCode": "ANA-TEST-2024-01",
    "status": "Phase 0 Active",
    "shortTitle": "Test analysis",
    "publicShortTitle": "Public test",
    "groups": {"leadingGroup": "HDBS", "subgroups": [], "otherGroups": []},
    "phase0": {"state": "Auxiliary metadata"},
}

SAMPLE_SEARCH = {
    "numberOfResults": 1,
    "results": [SAMPLE_ANALYSIS],
}

SAMPLE_PAPER = {
    "referenceCode": "HDBS-2024-01",
    "status": "Completed",
    "shortTitle": "Test paper",
}

SAMPLE_PAPER_SEARCH = {
    "numberOfResults": 1,
    "results": [SAMPLE_PAPER],
}

SAMPLE_CONF_NOTE = {
    "referenceCode": "ATLAS-CONF-2024-01",
    "status": "Phase 1 Closed",
    "shortTitle": "Test conf note",
}

SAMPLE_PUB_NOTE = {
    "referenceCode": "ATL-PHYS-PUB-2024-01",
    "status": "Phase 1 Active",
    "shortTitle": "Test pub note",
}

SAMPLE_ERROR = {"status": 404, "title": "Not Found", "detail": "Resource not found"}

SAMPLE_PUBLICATIONS = [
    {"referenceCode": "HDBS-2024-01", "type": "Paper"},
    {"referenceCode": "ATLAS-CONF-2024-01", "type": "ConfNote"},
]

SAMPLE_TRIGGERS = [
    {"name": "HLT_e60_lhmedium", "category": {"name": "electron", "year": "2024"}},
]


@pytest.fixture
def glance(test_settings: StareSettings) -> Glance:
    """Glance instance using a fixed token (no real auth)."""
    return Glance(settings=test_settings, token="fake-token")


# ---------------------------------------------------------------------------
# CERN cert bundle
# ---------------------------------------------------------------------------


def test_cern_cert_bundle_is_file() -> None:
    with as_file(files("stare.data").joinpath("CERN_chain.pem")) as p:
        assert p.is_file(), f"Expected cert bundle at {p}"
        assert "BEGIN CERTIFICATE" in p.read_text()


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

    assert isinstance(result, AnalysisSearchResult)
    assert result.number_of_results == 1
    assert len(result.results) == 1
    assert isinstance(result.results[0], Analysis)
    assert result.results[0].reference_code == "ANA-TEST-2024-01"


def test_analyses_search_passes_query_params(glance: Glance) -> None:
    with respx.mock(base_url=_BASE) as rx:
        rx.get("/searchAnalysis").mock(
            return_value=httpx.Response(200, json={"numberOfResults": 0, "results": []})
        )
        glance.analyses.search(query="referenceCode = X", limit=10, offset=5)
        params = dict(rx.calls[0].request.url.params)
    assert params["queryString"] == "referenceCode = X"
    assert params["limit"] == "10"
    assert params["offset"] == "5"


def test_analyses_search_sort_params(glance: Glance) -> None:
    with respx.mock(base_url=_BASE) as rx:
        rx.get("/searchAnalysis").mock(
            return_value=httpx.Response(200, json={"numberOfResults": 0, "results": []})
        )
        glance.analyses.search(sort_by="referenceCode", sort_desc=True)
        params = dict(rx.calls[0].request.url.params)
    assert params["sortBy"] == "referenceCode"
    assert params["sortDesc"] == "true"


def test_analyses_search_omits_none_params(glance: Glance) -> None:
    with respx.mock(base_url=_BASE) as rx:
        rx.get("/searchAnalysis").mock(
            return_value=httpx.Response(200, json={"numberOfResults": 0, "results": []})
        )
        glance.analyses.search()  # no query, no sort
        params = dict(rx.calls[0].request.url.params)
    assert "queryString" not in params
    assert "sortBy" not in params
    assert "sortDesc" not in params


def test_analyses_search_accepts_expression(glance: Glance) -> None:
    with respx.mock(base_url=_BASE) as rx:
        rx.get("/searchAnalysis").mock(
            return_value=httpx.Response(200, json={"numberOfResults": 0, "results": []})
        )
        glance.analyses.search(
            query=Condition(field="referenceCode", operator=Operator.EQ, value="X")
        )
        params = dict(rx.calls[0].request.url.params)
    assert params["queryString"] == "referenceCode = X"


def test_analyses_search_normalizes_snake_case_query(glance: Glance) -> None:
    with respx.mock(base_url=_BASE) as rx:
        rx.get("/searchAnalysis").mock(
            return_value=httpx.Response(200, json={"numberOfResults": 0, "results": []})
        )
        glance.analyses.search(query="reference_code = X")
        params = dict(rx.calls[0].request.url.params)
    assert params["queryString"] == "referenceCode = X"


def test_analyses_search_rejects_unknown_field(glance: Glance) -> None:
    with pytest.raises(DSLValidationError, match="unknown field"):
        glance.analyses.search(query="foo = bar")


def test_analyses_search_validate_false_passes_raw(glance: Glance) -> None:
    with respx.mock(base_url=_BASE) as rx:
        rx.get("/searchAnalysis").mock(
            return_value=httpx.Response(200, json={"numberOfResults": 0, "results": []})
        )
        glance.analyses.search(query="foo = bar", validate_query=False)
        params = dict(rx.calls[0].request.url.params)
    assert params["queryString"] == "foo = bar"


def test_papers_search_rejects_analysis_field(glance: Glance) -> None:
    with pytest.raises(DSLValidationError):
        glance.papers.search(query="phase0.state = ACTIVE")


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
# PaperResource.search
# ---------------------------------------------------------------------------


def test_papers_search_returns_paper_search_result(glance: Glance) -> None:
    with respx.mock(base_url=_BASE) as rx:
        rx.get("/searchPaper").mock(
            return_value=httpx.Response(200, json=SAMPLE_PAPER_SEARCH)
        )
        result = glance.papers.search()

    assert isinstance(result, PaperSearchResult)
    assert result.number_of_results == 1
    assert len(result.results) == 1
    assert isinstance(result.results[0], Paper)
    assert result.results[0].reference_code == "HDBS-2024-01"


def test_papers_search_passes_query_params(glance: Glance) -> None:
    with respx.mock(base_url=_BASE) as rx:
        rx.get("/searchPaper").mock(
            return_value=httpx.Response(200, json={"numberOfResults": 0, "results": []})
        )
        glance.papers.search(query="referenceCode = X", limit=10, offset=5)
        params = dict(rx.calls[0].request.url.params)
    assert params["queryString"] == "referenceCode = X"
    assert params["limit"] == "10"
    assert params["offset"] == "5"


def test_papers_search_omits_none_params(glance: Glance) -> None:
    with respx.mock(base_url=_BASE) as rx:
        rx.get("/searchPaper").mock(
            return_value=httpx.Response(200, json={"numberOfResults": 0, "results": []})
        )
        glance.papers.search()
        params = dict(rx.calls[0].request.url.params)
    assert "queryString" not in params
    assert "sortBy" not in params
    assert "sortDesc" not in params


# ---------------------------------------------------------------------------
# ConfNoteResource.get
# ---------------------------------------------------------------------------


def test_conf_notes_get_returns_conf_note(glance: Glance) -> None:
    with respx.mock(base_url=_BASE) as rx:
        rx.get("/confnotes/ATLAS-CONF-2024-01").mock(
            return_value=httpx.Response(200, json=SAMPLE_CONF_NOTE)
        )
        result = glance.conf_notes.get("ATLAS-CONF-2024-01")

    assert isinstance(result, ConfNote)
    assert result.reference_code == "ATLAS-CONF-2024-01"


# ---------------------------------------------------------------------------
# PubNoteResource.get
# ---------------------------------------------------------------------------


def test_pub_notes_get_returns_pub_note(glance: Glance) -> None:
    with respx.mock(base_url=_BASE) as rx:
        rx.get("/pubnotes/ATL-PHYS-PUB-2024-01").mock(
            return_value=httpx.Response(200, json=SAMPLE_PUB_NOTE)
        )
        result = glance.pub_notes.get("ATL-PHYS-PUB-2024-01")

    assert isinstance(result, PubNote)
    assert result.reference_code == "ATL-PHYS-PUB-2024-01"


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


# ---------------------------------------------------------------------------
# ResponseParseError on invalid response bodies
# ---------------------------------------------------------------------------


def test_analyses_search_raises_response_parse_error(glance: Glance) -> None:
    """A 200 response that fails model validation raises ResponseParseError."""
    bad_json = {"results": "not-a-list"}
    with respx.mock(base_url=_BASE) as rx:
        rx.get("/searchAnalysis").mock(return_value=httpx.Response(200, json=bad_json))
        with pytest.raises(ResponseParseError) as exc_info:
            glance.analyses.search()
    msg = str(exc_info.value)
    assert "AnalysisSearchResult" in msg
    assert "results" in msg
    assert "validation error" in msg.lower()
    # default verbose=False -> raw_data is not attached
    assert exc_info.value.raw_data is None
    # details are always enriched with snippet + location info
    assert exc_info.value.details
    assert any("results" in d.loc_str for d in exc_info.value.details)


def test_analyses_search_verbose_attaches_raw_data(glance: Glance) -> None:
    """verbose=True attaches the raw payload to ResponseParseError."""
    bad_json = {"results": "not-a-list"}
    with respx.mock(base_url=_BASE) as rx:
        rx.get("/searchAnalysis").mock(return_value=httpx.Response(200, json=bad_json))
        with pytest.raises(ResponseParseError) as exc_info:
            glance.analyses.search(verbose=True)
    assert exc_info.value.raw_data == bad_json


def test_papers_search_verbose_attaches_raw_data(glance: Glance) -> None:
    """verbose=True on paper search attaches the raw payload."""
    bad_json = {"results": "not-a-list"}
    with respx.mock(base_url=_BASE) as rx:
        rx.get("/searchPaper").mock(return_value=httpx.Response(200, json=bad_json))
        with pytest.raises(ResponseParseError) as exc_info:
            glance.papers.search(verbose=True)
    assert exc_info.value.raw_data == bad_json


def test_conf_notes_get_verbose_attaches_raw_data(glance: Glance) -> None:
    """verbose=True on conf_notes.get attaches the raw payload."""
    bad_json = {"analysisTeam": "not-a-list"}
    with respx.mock(base_url=_BASE) as rx:
        rx.get("/confnotes/ATL-PHYS-PUB-2024-01").mock(
            return_value=httpx.Response(200, json=bad_json)
        )
        with pytest.raises(ResponseParseError) as exc_info:
            glance.conf_notes.get("ATL-PHYS-PUB-2024-01", verbose=True)
    assert exc_info.value.raw_data == bad_json


def test_response_parse_error_is_stare_error(glance: Glance) -> None:
    """ResponseParseError is a StareError so existing CLI handlers catch it."""
    with respx.mock(base_url=_BASE) as rx:
        rx.get("/searchAnalysis").mock(
            return_value=httpx.Response(200, json={"results": "not-a-list"})
        )
        with pytest.raises(StareError):
            glance.analyses.search()


# ---------------------------------------------------------------------------
# _format_parse_error
# ---------------------------------------------------------------------------


def test_format_parse_error_with_nested_loc() -> None:
    """loc entries are dot-joined and integer indices appear as numbers."""

    # Use plain BaseModel (not _Base) to get a raw ValidationError
    class _Tmp(PydanticBase):
        items: list[str]

    try:
        _Tmp.model_validate({"items": "not-a-list"})
    except ValidationError as exc:
        msg, _details = _format_parse_error("_Tmp", exc)

    assert "_Tmp" in msg
    assert "items" in msg
    assert "1." in msg  # numbered entry


def test_format_parse_error_integer_index_uses_brackets() -> None:
    """Integer indices in loc appear as [n], not .n."""

    class _M(PydanticBase):
        items: list[str]

    try:
        _M.model_validate({"items": ["ok", 123]})
    except ValidationError as exc:
        msg, _details = _format_parse_error("_M", exc)

    assert "items[1]" in msg


def test_format_parse_error_with_obj_extracts_reference_code() -> None:
    """When obj is provided, referenceCode is extracted from the parent at the error loc."""
    mock_error = MagicMock()
    mock_error.errors.return_value = [
        {
            "loc": ("results", 2, "extraMetadata"),
            "msg": "bad value",
            "type": "value_error",
            "input": "bad",
        }
    ]
    obj = {
        "results": [
            {"referenceCode": "ANA-A"},
            {"referenceCode": "ANA-B"},
            {"referenceCode": "ANA-C"},
        ]
    }
    msg, _details = _format_parse_error("SearchResult", mock_error, obj=obj)
    assert "results[2]" in msg
    assert "ANA-C" in msg


def test_format_parse_error_empty_loc() -> None:
    """When loc is empty the location shows as '(root)'."""
    mock_error = MagicMock()
    mock_error.errors.return_value = [
        {"loc": (), "msg": "something broke", "type": "value_error"}
    ]

    msg, _details = _format_parse_error("MyModel", mock_error)
    assert "(root)" in msg
    assert "something broke" in msg

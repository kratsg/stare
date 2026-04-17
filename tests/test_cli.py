"""Tests for the stare CLI (typer commands)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from stare import __version__
from stare.cli import app
from stare.exceptions import AuthenticationError, NotFoundError
from stare.models import (
    Analysis,
    ConfNote,
    Paper,
    PaperSearchResult,
    PublicationRef,
    PubNote,
    SearchResult,
    Trigger,
)
from stare.models.auth import JwtClaims, TokenInfo

runner = CliRunner()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_ANALYSIS = Analysis.model_validate(
    {
        "referenceCode": "ANA-TEST-2024-01",
        "status": "Active",
        "shortTitle": "Test analysis",
    }
)

SAMPLE_PAPER = Paper.model_validate(
    {
        "referenceCode": "HDBS-2024-01",
        "status": "Published",
        "shortTitle": "Test paper",
    }
)

SAMPLE_CONF_NOTE = ConfNote.model_validate(
    {
        "temporaryReferenceCode": "ATLAS-CONF-2024-001",
        "status": "Active",
        "shortTitle": "Test conf note",
    }
)

SAMPLE_PUB_NOTE = PubNote.model_validate(
    {
        "temporaryReferenceCode": "ATL-PHYS-PUB-2024-001",
        "status": "Active",
        "shortTitle": "Test pub note",
    }
)

SAMPLE_SEARCH = SearchResult.model_validate(
    {
        "totalRows": 1,
        "results": [
            {
                "referenceCode": "ANA-TEST-2024-01",
                "status": "Active",
                "shortTitle": "Test analysis",
            }
        ],
    }
)

SAMPLE_PAPER_SEARCH = PaperSearchResult.model_validate(
    {
        "numberOfResults": "1",
        "results": [
            {
                "referenceCode": "HDBS-2024-01",
                "status": "Published",
                "shortTitle": "Test paper",
            }
        ],
    }
)

SAMPLE_PUBLICATIONS = [
    PublicationRef.model_validate({"referenceCode": "HDBS-2024-01", "type": "Paper"}),
]

SAMPLE_TRIGGERS = [
    Trigger.model_validate(
        {"name": "HLT_e60", "category": {"name": "electron", "year": "2024"}}
    ),
]


def _mock_glance(**overrides: object) -> MagicMock:
    """Return a MagicMock shaped like a Glance instance."""
    g = MagicMock()
    g.analyses.search.return_value = SAMPLE_SEARCH
    g.analyses.get.return_value = SAMPLE_ANALYSIS
    g.papers.search.return_value = SAMPLE_PAPER_SEARCH
    g.papers.get.return_value = SAMPLE_PAPER
    g.conf_notes.get.return_value = SAMPLE_CONF_NOTE
    g.pub_notes.get.return_value = SAMPLE_PUB_NOTE
    g.publications.search.return_value = SAMPLE_PUBLICATIONS
    g.groups.list.return_value = ["HDBS", "SUSY"]
    g.subgroups.list.return_value = ["Higgs", "Dibosons"]
    g.triggers.search.return_value = SAMPLE_TRIGGERS
    for k, v in overrides.items():
        setattr(g, k, v)
    return g


# ---------------------------------------------------------------------------
# version
# ---------------------------------------------------------------------------


def test_version_command() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.output


# ---------------------------------------------------------------------------
# login / logout / auth status
# ---------------------------------------------------------------------------


def test_auth_login_command_calls_token_manager() -> None:
    mock_tm = MagicMock()
    mock_tm.login.return_value = None
    with patch("stare.cli._make_token_manager", return_value=mock_tm):
        result = runner.invoke(app, ["auth", "login"])
    assert result.exit_code == 0
    mock_tm.login.assert_called_once()


def test_auth_login_shows_error_on_failure() -> None:
    mock_tm = MagicMock()
    mock_tm.login.side_effect = AuthenticationError("Auth failed")
    with patch("stare.cli._make_token_manager", return_value=mock_tm):
        result = runner.invoke(app, ["auth", "login"])
    assert result.exit_code != 0
    assert "Auth failed" in result.output


def test_auth_logout_command_calls_token_manager() -> None:
    mock_tm = MagicMock()
    with patch("stare.cli._make_token_manager", return_value=mock_tm):
        result = runner.invoke(app, ["auth", "logout"])
    assert result.exit_code == 0
    mock_tm.logout.assert_called_once()


def test_auth_status_authenticated() -> None:
    mock_tm = MagicMock()
    mock_tm.is_authenticated.return_value = True
    with patch("stare.cli._make_token_manager", return_value=mock_tm):
        result = runner.invoke(app, ["auth", "status"])
    assert result.exit_code == 0
    assert "authenticated" in result.output.lower()


def test_auth_status_not_authenticated() -> None:
    mock_tm = MagicMock()
    mock_tm.is_authenticated.return_value = False
    with patch("stare.cli._make_token_manager", return_value=mock_tm):
        result = runner.invoke(app, ["auth", "status"])
    assert result.exit_code == 0
    assert "not authenticated" in result.output.lower()


def test_auth_info_shows_claims() -> None:
    mock_tm = MagicMock()
    mock_tm.get_token_info.return_value = TokenInfo(
        is_expired=False,
        expires_at=int(__import__("time").time()) + 3600,
        claims=JwtClaims(
            preferred_username="kratsg",
            name="Giordon Stark",
            email="kratsg@cern.ch",
            sub="abc123",
        ),
    )
    with patch("stare.cli._make_token_manager", return_value=mock_tm):
        result = runner.invoke(app, ["auth", "info"])
    assert result.exit_code == 0
    assert "kratsg" in result.output
    assert "Giordon Stark" in result.output


def test_auth_info_unauthenticated() -> None:
    mock_tm = MagicMock()
    mock_tm.get_token_info.return_value = None
    with patch("stare.cli._make_token_manager", return_value=mock_tm):
        result = runner.invoke(app, ["auth", "info"])
    assert result.exit_code != 0


def test_auth_info_shows_expired_when_token_expired() -> None:
    mock_tm = MagicMock()
    mock_tm.get_token_info.return_value = TokenInfo(
        is_expired=True,
        expires_at=int(__import__("time").time()) - 3600,
        claims=JwtClaims(preferred_username="kratsg"),
    )
    with patch("stare.cli._make_token_manager", return_value=mock_tm):
        result = runner.invoke(app, ["auth", "info"])
    assert result.exit_code == 0
    assert "expired" in result.output.lower()


def test_auth_info_shows_roles() -> None:
    mock_tm = MagicMock()
    mock_tm.get_token_info.return_value = TokenInfo(
        is_expired=False,
        expires_at=int(__import__("time").time()) + 3600,
        claims=JwtClaims(
            preferred_username="kratsg",
            name="Giordon Stark",
            cern_roles=["stare-user", "default-role"],
        ),
    )
    with patch("stare.cli._make_token_manager", return_value=mock_tm):
        result = runner.invoke(app, ["auth", "info"])
    assert result.exit_code == 0
    assert "stare-user" in result.output


def test_auth_info_exchange_shows_claims() -> None:
    mock_tm = MagicMock()
    mock_tm.get_exchange_token_info.return_value = TokenInfo(
        is_expired=False,
        expires_at=int(__import__("time").time()) + 3600,
        claims=JwtClaims(
            preferred_username="han.solo",
            name="Han Solo",
            cern_roles=["stare-user"],
        ),
    )
    with patch("stare.cli._make_token_manager", return_value=mock_tm):
        result = runner.invoke(app, ["auth", "info", "--exchange"])
    assert result.exit_code == 0
    assert "han.solo" in result.output
    assert "stare-user" in result.output


def test_auth_info_exchange_no_audience_shows_error() -> None:
    mock_tm = MagicMock()
    mock_tm.get_exchange_token_info.return_value = None
    with patch("stare.cli._make_token_manager", return_value=mock_tm):
        result = runner.invoke(app, ["auth", "info", "--exchange"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# analysis search
# ---------------------------------------------------------------------------


def test_analysis_search_default() -> None:
    with patch("stare.cli._make_glance", return_value=_mock_glance()):
        result = runner.invoke(app, ["analysis", "search"])
    assert result.exit_code == 0
    assert "ANA-TEST-2024-01" in result.output


def test_analysis_search_with_query() -> None:
    g = _mock_glance()
    with patch("stare.cli._make_glance", return_value=g):
        result = runner.invoke(app, ["analysis", "search", "--query", "test"])
    assert result.exit_code == 0
    g.analyses.search.assert_called_once()
    call_kwargs = g.analyses.search.call_args.kwargs
    assert call_kwargs["query"] == "test"


def test_analysis_search_json_output() -> None:
    with patch("stare.cli._make_glance", return_value=_mock_glance()):
        result = runner.invoke(app, ["analysis", "search", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "totalRows" in data or "total_rows" in data


def test_analysis_search_with_limit_and_offset() -> None:
    g = _mock_glance()
    with patch("stare.cli._make_glance", return_value=g):
        runner.invoke(app, ["analysis", "search", "--limit", "10", "--offset", "5"])
    call_kwargs = g.analyses.search.call_args.kwargs
    assert call_kwargs["limit"] == 10
    assert call_kwargs["offset"] == 5


# ---------------------------------------------------------------------------
# analysis get
# ---------------------------------------------------------------------------


def test_analysis_get_command() -> None:
    with patch("stare.cli._make_glance", return_value=_mock_glance()):
        result = runner.invoke(app, ["analysis", "get", "ANA-TEST-2024-01"])
    assert result.exit_code == 0
    assert "ANA-TEST-2024-01" in result.output


def test_analysis_get_json_output() -> None:
    with patch("stare.cli._make_glance", return_value=_mock_glance()):
        result = runner.invoke(app, ["analysis", "get", "ANA-TEST-2024-01", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data.get("referenceCode") == "ANA-TEST-2024-01"


def test_analysis_get_not_found() -> None:
    g = _mock_glance()
    g.analyses.get.side_effect = NotFoundError(404, "Not Found", "No such analysis")
    with patch("stare.cli._make_glance", return_value=g):
        result = runner.invoke(app, ["analysis", "get", "MISSING"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# paper search
# ---------------------------------------------------------------------------


def test_paper_search_default() -> None:
    with patch("stare.cli._make_glance", return_value=_mock_glance()):
        result = runner.invoke(app, ["paper", "search"])
    assert result.exit_code == 0
    assert "HDBS-2024-01" in result.output


def test_paper_search_with_query() -> None:
    g = _mock_glance()
    with patch("stare.cli._make_glance", return_value=g):
        result = runner.invoke(app, ["paper", "search", "--query", "test"])
    assert result.exit_code == 0
    g.papers.search.assert_called_once()
    call_kwargs = g.papers.search.call_args.kwargs
    assert call_kwargs["query"] == "test"


def test_paper_search_json_output() -> None:
    with patch("stare.cli._make_glance", return_value=_mock_glance()):
        result = runner.invoke(app, ["paper", "search", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "numberOfResults" in data or "number_of_results" in data


def test_paper_search_with_limit_and_offset() -> None:
    g = _mock_glance()
    with patch("stare.cli._make_glance", return_value=g):
        runner.invoke(app, ["paper", "search", "--limit", "10", "--offset", "5"])
    call_kwargs = g.papers.search.call_args.kwargs
    assert call_kwargs["limit"] == 10
    assert call_kwargs["offset"] == 5


# ---------------------------------------------------------------------------
# paper get
# ---------------------------------------------------------------------------


def test_paper_get_command() -> None:
    with patch("stare.cli._make_glance", return_value=_mock_glance()):
        result = runner.invoke(app, ["paper", "get", "HDBS-2024-01"])
    assert result.exit_code == 0
    assert "HDBS-2024-01" in result.output


def test_paper_get_json_output() -> None:
    with patch("stare.cli._make_glance", return_value=_mock_glance()):
        result = runner.invoke(app, ["paper", "get", "HDBS-2024-01", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data.get("referenceCode") == "HDBS-2024-01"


# ---------------------------------------------------------------------------
# conf-note
# ---------------------------------------------------------------------------


def test_conf_note_command() -> None:
    with patch("stare.cli._make_glance", return_value=_mock_glance()):
        result = runner.invoke(app, ["conf-note", "ATLAS-CONF-2024-001"])
    assert result.exit_code == 0
    assert "ATLAS-CONF-2024-001" in result.output


def test_conf_note_json_output() -> None:
    with patch("stare.cli._make_glance", return_value=_mock_glance()):
        result = runner.invoke(app, ["conf-note", "ATLAS-CONF-2024-001", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data.get("temporaryReferenceCode") == "ATLAS-CONF-2024-001"


# ---------------------------------------------------------------------------
# pub-note
# ---------------------------------------------------------------------------


def test_pub_note_command() -> None:
    with patch("stare.cli._make_glance", return_value=_mock_glance()):
        result = runner.invoke(app, ["pub-note", "ATL-PHYS-PUB-2024-001"])
    assert result.exit_code == 0
    assert "ATL-PHYS-PUB-2024-001" in result.output


def test_pub_note_json_output() -> None:
    with patch("stare.cli._make_glance", return_value=_mock_glance()):
        result = runner.invoke(app, ["pub-note", "ATL-PHYS-PUB-2024-001", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data.get("temporaryReferenceCode") == "ATL-PHYS-PUB-2024-001"


# ---------------------------------------------------------------------------
# publications search
# ---------------------------------------------------------------------------


def test_publications_search_command() -> None:
    with patch("stare.cli._make_glance", return_value=_mock_glance()):
        result = runner.invoke(app, ["publications", "search"])
    assert result.exit_code == 0
    assert "HDBS-2024-01" in result.output


def test_publications_search_json() -> None:
    with patch("stare.cli._make_glance", return_value=_mock_glance()):
        result = runner.invoke(app, ["publications", "search", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)


def test_publications_search_with_type_filter() -> None:
    g = _mock_glance()
    with patch("stare.cli._make_glance", return_value=g):
        runner.invoke(app, ["publications", "search", "--type", "Paper"])
    call_kwargs = g.publications.search.call_args.kwargs
    assert "Paper" in call_kwargs.get("types", [])


# ---------------------------------------------------------------------------
# groups / subgroups
# ---------------------------------------------------------------------------


def test_groups_command() -> None:
    with patch("stare.cli._make_glance", return_value=_mock_glance()):
        result = runner.invoke(app, ["groups"])
    assert result.exit_code == 0
    assert "HDBS" in result.output


def test_groups_json_output() -> None:
    with patch("stare.cli._make_glance", return_value=_mock_glance()):
        result = runner.invoke(app, ["groups", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "HDBS" in data


def test_subgroups_command() -> None:
    with patch("stare.cli._make_glance", return_value=_mock_glance()):
        result = runner.invoke(app, ["subgroups"])
    assert result.exit_code == 0
    assert "Higgs" in result.output


# ---------------------------------------------------------------------------
# triggers search
# ---------------------------------------------------------------------------


def test_triggers_search_command() -> None:
    with patch("stare.cli._make_glance", return_value=_mock_glance()):
        result = runner.invoke(app, ["triggers", "search"])
    assert result.exit_code == 0
    assert "HLT_e60" in result.output


def test_triggers_search_json() -> None:
    with patch("stare.cli._make_glance", return_value=_mock_glance()):
        result = runner.invoke(app, ["triggers", "search", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)


def test_triggers_search_with_category_filter() -> None:
    g = _mock_glance()
    with patch("stare.cli._make_glance", return_value=g):
        runner.invoke(app, ["triggers", "search", "--category", "electron"])
    call_kwargs = g.triggers.search.call_args.kwargs
    assert "electron" in call_kwargs.get("categories", [])

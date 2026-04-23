"""Tests for the stare CLI (typer commands)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from stare import __version__
from stare.cli import app
from stare.dsl.errors import DSLValidationError
from stare.exceptions import (
    AuthenticationError,
    EnrichedErrorResponse,
    NotFoundError,
    ResponseParseError,
)
from stare.models import (
    Analysis,
    AnalysisSearchResult,
    ConfNote,
    ConfNoteSearchResult,
    Paper,
    PaperSearchResult,
    PublicationRef,
    PubNote,
    PubNoteSearchResult,
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
        "status": "Created",
        "shortTitle": "Test analysis",
    }
)

SAMPLE_PAPER = Paper.model_validate(
    {
        "referenceCode": "HDBS-2024-01",
        "status": "Phase 1 Active",
        "shortTitle": "Test paper",
    }
)

SAMPLE_CONF_NOTE = ConfNote.model_validate(
    {
        "temporaryReferenceCode": "ATLAS-CONF-2024-01",
        "status": "Completed",
        "shortTitle": "Test conf note",
    }
)

SAMPLE_PUB_NOTE = PubNote.model_validate(
    {
        "finalReferenceCode": "ATL-PHYS-PUB-2024-01",
        "status": "Phase 1 Closed",
        "shortTitle": "Test pub note",
    }
)

SAMPLE_SEARCH = AnalysisSearchResult.model_validate(
    {
        "numberOfResults": 1,
        "results": [
            {
                "referenceCode": "ANA-TEST-2024-01",
                "status": "Phase 0 Active",
                "shortTitle": "Test analysis",
            }
        ],
    }
)

SAMPLE_PAPER_SEARCH = PaperSearchResult.model_validate(
    {
        "numberOfResults": 1,
        "results": [
            {
                "referenceCode": "HDBS-2024-01",
                "status": "Phase 2 Active",
                "shortTitle": "Test paper",
            }
        ],
    }
)

SAMPLE_CONF_NOTE_SEARCH = ConfNoteSearchResult.model_validate(
    {
        "numberOfResults": 1,
        "results": [
            {
                "temporaryReferenceCode": "ATLAS-CONF-2024-01",
                "finalReferenceCode": "ATLAS-CONF-2024-001",
                "status": "Completed",
                "shortTitle": "Test conf note",
            }
        ],
    }
)

SAMPLE_PUB_NOTE_SEARCH = PubNoteSearchResult.model_validate(
    {
        "numberOfResults": 1,
        "results": [
            {
                "finalReferenceCode": "ATL-PHYS-PUB-2024-01",
                "status": "Phase 1 Closed",
                "shortTitle": "Test pub note",
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
    g.confnotes.search.return_value = SAMPLE_CONF_NOTE_SEARCH
    g.confnotes.get.return_value = SAMPLE_CONF_NOTE
    g.pubnotes.search.return_value = SAMPLE_PUB_NOTE_SEARCH
    g.pubnotes.get.return_value = SAMPLE_PUB_NOTE
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
    with patch("stare.cli.utils.make_token_manager", return_value=mock_tm):
        result = runner.invoke(app, ["auth", "login"])
    assert result.exit_code == 0
    mock_tm.login.assert_called_once()


def test_auth_login_shows_error_on_failure() -> None:
    mock_tm = MagicMock()
    mock_tm.login.side_effect = AuthenticationError("Auth failed")
    with patch("stare.cli.utils.make_token_manager", return_value=mock_tm):
        result = runner.invoke(app, ["auth", "login"])
    assert result.exit_code != 0
    assert "Auth failed" in result.output


def test_auth_logout_command_calls_token_manager() -> None:
    mock_tm = MagicMock()
    with patch("stare.cli.utils.make_token_manager", return_value=mock_tm):
        result = runner.invoke(app, ["auth", "logout"])
    assert result.exit_code == 0
    mock_tm.logout.assert_called_once()


def test_auth_status_authenticated() -> None:
    mock_tm = MagicMock()
    mock_tm.is_authenticated.return_value = True
    with patch("stare.cli.utils.make_token_manager", return_value=mock_tm):
        result = runner.invoke(app, ["auth", "status"])
    assert result.exit_code == 0
    assert "authenticated" in result.output.lower()


def test_auth_status_not_authenticated() -> None:
    mock_tm = MagicMock()
    mock_tm.is_authenticated.return_value = False
    with patch("stare.cli.utils.make_token_manager", return_value=mock_tm):
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
    with patch("stare.cli.utils.make_token_manager", return_value=mock_tm):
        result = runner.invoke(app, ["auth", "info"])
    assert result.exit_code == 0
    assert "kratsg" in result.output
    assert "Giordon Stark" in result.output


def test_auth_info_unauthenticated() -> None:
    mock_tm = MagicMock()
    mock_tm.get_token_info.return_value = None
    with patch("stare.cli.utils.make_token_manager", return_value=mock_tm):
        result = runner.invoke(app, ["auth", "info"])
    assert result.exit_code != 0


def test_auth_info_shows_expired_when_token_expired() -> None:
    mock_tm = MagicMock()
    mock_tm.get_token_info.return_value = TokenInfo(
        is_expired=True,
        expires_at=int(__import__("time").time()) - 3600,
        claims=JwtClaims(preferred_username="kratsg"),
    )
    with patch("stare.cli.utils.make_token_manager", return_value=mock_tm):
        result = runner.invoke(app, ["auth", "info"])
    assert result.exit_code == 0
    assert "expired" in result.output.lower()


def test_auth_info_shows_audience_string() -> None:
    mock_tm = MagicMock()
    mock_tm.get_token_info.return_value = TokenInfo(
        is_expired=False,
        expires_at=int(__import__("time").time()) + 3600,
        claims=JwtClaims(preferred_username="han.solo", aud="atlas-glance-api"),
    )
    with patch("stare.cli.utils.make_token_manager", return_value=mock_tm):
        result = runner.invoke(app, ["auth", "info"])
    assert result.exit_code == 0
    assert "atlas-glance-api" in result.output


def test_auth_info_shows_audience_list() -> None:
    mock_tm = MagicMock()
    mock_tm.get_token_info.return_value = TokenInfo(
        is_expired=False,
        expires_at=int(__import__("time").time()) + 3600,
        claims=JwtClaims(preferred_username="han.solo", aud=["api-a", "api-b"]),
    )
    with patch("stare.cli.utils.make_token_manager", return_value=mock_tm):
        result = runner.invoke(app, ["auth", "info"])
    assert result.exit_code == 0
    assert "api-a" in result.output
    assert "api-b" in result.output


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
    with patch("stare.cli.utils.make_token_manager", return_value=mock_tm):
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
    with patch("stare.cli.utils.make_token_manager", return_value=mock_tm):
        result = runner.invoke(app, ["auth", "info", "--exchange"])
    assert result.exit_code == 0
    assert "han.solo" in result.output
    assert "stare-user" in result.output


def test_auth_info_exchange_no_audience_shows_error() -> None:
    mock_tm = MagicMock()
    mock_tm.get_exchange_token_info.return_value = None
    with patch("stare.cli.utils.make_token_manager", return_value=mock_tm):
        result = runner.invoke(app, ["auth", "info", "--exchange"])
    assert result.exit_code != 0


def test_auth_info_access_token_prints_raw() -> None:
    mock_tm = MagicMock()
    mock_tm.get_pkce_access_token.return_value = "raw-pkce-access"
    with patch("stare.cli.utils.make_token_manager", return_value=mock_tm):
        result = runner.invoke(app, ["auth", "info", "--access-token"])
    assert result.exit_code == 0
    assert "raw-pkce-access" in result.output


def test_auth_info_id_token_prints_raw() -> None:
    mock_tm = MagicMock()
    mock_tm.get_pkce_id_token.return_value = "raw-id-token"
    with patch("stare.cli.utils.make_token_manager", return_value=mock_tm):
        result = runner.invoke(app, ["auth", "info", "--id-token"])
    assert result.exit_code == 0
    assert "raw-id-token" in result.output


def test_auth_info_id_token_missing_shows_error() -> None:
    mock_tm = MagicMock()
    mock_tm.get_pkce_id_token.return_value = None
    with patch("stare.cli.utils.make_token_manager", return_value=mock_tm):
        result = runner.invoke(app, ["auth", "info", "--id-token"])
    assert result.exit_code != 0


def test_auth_info_exchange_access_token_prints_raw() -> None:
    mock_tm = MagicMock()
    mock_tm.get_exchange_access_token.return_value = "raw-exchange-access"
    with patch("stare.cli.utils.make_token_manager", return_value=mock_tm):
        result = runner.invoke(app, ["auth", "info", "--exchange", "--access-token"])
    assert result.exit_code == 0
    assert "raw-exchange-access" in result.output


def test_auth_info_exchange_access_token_no_audience_shows_error() -> None:
    mock_tm = MagicMock()
    mock_tm.get_exchange_access_token.return_value = None
    with patch("stare.cli.utils.make_token_manager", return_value=mock_tm):
        result = runner.invoke(app, ["auth", "info", "--exchange", "--access-token"])
    assert result.exit_code != 0


def test_auth_info_exchange_id_token_shows_error() -> None:
    mock_tm = MagicMock()
    with patch("stare.cli.utils.make_token_manager", return_value=mock_tm):
        result = runner.invoke(app, ["auth", "info", "--exchange", "--id-token"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# analysis search
# ---------------------------------------------------------------------------


def test_analysis_search_default() -> None:
    with patch("stare.cli.utils.make_glance", return_value=_mock_glance()):
        result = runner.invoke(app, ["analysis", "search"])
    assert result.exit_code == 0
    assert "ANA-TEST-2024-01" in result.output


def test_analysis_search_with_query() -> None:
    g = _mock_glance()
    with patch("stare.cli.utils.make_glance", return_value=g):
        result = runner.invoke(app, ["analysis", "search", "--query", "test"])
    assert result.exit_code == 0
    g.analyses.search.assert_called_once()
    call_kwargs = g.analyses.search.call_args.kwargs
    assert call_kwargs["query"] == "test"


def test_analysis_search_no_validate_flag() -> None:
    g = _mock_glance()
    with patch("stare.cli.utils.make_glance", return_value=g):
        result = runner.invoke(
            app, ["analysis", "search", "--query", "foo", "--no-validate"]
        )
    assert result.exit_code == 0
    call_kwargs = g.analyses.search.call_args.kwargs
    assert call_kwargs["validate_query"] is False


def test_analysis_search_dsl_error_shown_as_bad_parameter() -> None:
    g = _mock_glance()
    g.analyses.search.side_effect = DSLValidationError("unknown field 'foo'")
    with patch("stare.cli.utils.make_glance", return_value=g):
        result = runner.invoke(app, ["analysis", "search", "--query", "foo = bar"])
    assert result.exit_code != 0
    assert "unknown field" in result.output


def test_analysis_search_json_output() -> None:
    with patch("stare.cli.utils.make_glance", return_value=_mock_glance()):
        result = runner.invoke(app, ["analysis", "search", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "numberOfResults" in data


def test_analysis_search_with_limit_and_offset() -> None:
    g = _mock_glance()
    with patch("stare.cli.utils.make_glance", return_value=g):
        runner.invoke(app, ["analysis", "search", "--limit", "10", "--offset", "5"])
    call_kwargs = g.analyses.search.call_args.kwargs
    assert call_kwargs["limit"] == 10
    assert call_kwargs["offset"] == 5


def test_analysis_search_not_enough_results() -> None:
    g = _mock_glance()
    with patch("stare.cli.utils.make_glance", return_value=g):
        result = runner.invoke(
            app, ["analysis", "search", "--limit", "10", "--offset", "5"]
        )
    assert result.exit_code == 2


# ---------------------------------------------------------------------------
# analysis get
# ---------------------------------------------------------------------------


def test_analysis_get_command() -> None:
    with patch("stare.cli.utils.make_glance", return_value=_mock_glance()):
        result = runner.invoke(app, ["analysis", "get", "ANA-TEST-2024-01"])
    assert result.exit_code == 0
    assert "ANA-TEST-2024-01" in result.output


def test_analysis_get_json_output() -> None:
    with patch("stare.cli.utils.make_glance", return_value=_mock_glance()):
        result = runner.invoke(app, ["analysis", "get", "ANA-TEST-2024-01", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data.get("referenceCode") == "ANA-TEST-2024-01"


def test_analysis_get_not_found() -> None:
    g = _mock_glance()
    g.analyses.get.side_effect = NotFoundError(404, "Not Found", "No such analysis")
    with patch("stare.cli.utils.make_glance", return_value=g):
        result = runner.invoke(app, ["analysis", "get", "MISSING"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# paper search
# ---------------------------------------------------------------------------


def test_paper_search_default() -> None:
    with patch("stare.cli.utils.make_glance", return_value=_mock_glance()):
        result = runner.invoke(app, ["paper", "search"])
    assert result.exit_code == 0
    assert "HDBS-2024-01" in result.output


def test_paper_search_with_query() -> None:
    g = _mock_glance()
    with patch("stare.cli.utils.make_glance", return_value=g):
        result = runner.invoke(app, ["paper", "search", "--query", "test"])
    assert result.exit_code == 0
    g.papers.search.assert_called_once()
    call_kwargs = g.papers.search.call_args.kwargs
    assert call_kwargs["query"] == "test"


def test_paper_search_no_validate_flag() -> None:
    g = _mock_glance()
    with patch("stare.cli.utils.make_glance", return_value=g):
        result = runner.invoke(
            app, ["paper", "search", "--query", "foo", "--no-validate"]
        )
    assert result.exit_code == 0
    call_kwargs = g.papers.search.call_args.kwargs
    assert call_kwargs["validate_query"] is False


def test_paper_search_dsl_error_shown_as_bad_parameter() -> None:
    g = _mock_glance()
    g.papers.search.side_effect = DSLValidationError("unknown field 'bar'")
    with patch("stare.cli.utils.make_glance", return_value=g):
        result = runner.invoke(app, ["paper", "search", "--query", "bar = baz"])
    assert result.exit_code != 0
    assert "unknown field" in result.output


def test_paper_search_json_output() -> None:
    with patch("stare.cli.utils.make_glance", return_value=_mock_glance()):
        result = runner.invoke(app, ["paper", "search", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "numberOfResults" in data


def test_paper_search_with_limit_and_offset() -> None:
    g = _mock_glance()
    with patch("stare.cli.utils.make_glance", return_value=g):
        runner.invoke(app, ["paper", "search", "--limit", "10", "--offset", "5"])
    call_kwargs = g.papers.search.call_args.kwargs
    assert call_kwargs["limit"] == 10
    assert call_kwargs["offset"] == 5


def test_paper_search_not_enough_results() -> None:
    g = _mock_glance()
    with patch("stare.cli.utils.make_glance", return_value=g):
        result = runner.invoke(
            app, ["paper", "search", "--limit", "10", "--offset", "5"]
        )
    assert result.exit_code == 2


# ---------------------------------------------------------------------------
# paper get
# ---------------------------------------------------------------------------


def test_paper_get_command() -> None:
    with patch("stare.cli.utils.make_glance", return_value=_mock_glance()):
        result = runner.invoke(app, ["paper", "get", "HDBS-2024-01"])
    assert result.exit_code == 0
    assert "HDBS-2024-01" in result.output


def test_paper_get_json_output() -> None:
    with patch("stare.cli.utils.make_glance", return_value=_mock_glance()):
        result = runner.invoke(app, ["paper", "get", "HDBS-2024-01", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data.get("referenceCode") == "HDBS-2024-01"


# ---------------------------------------------------------------------------
# confnote get
# ---------------------------------------------------------------------------


def test_confnote_get_command() -> None:
    g = _mock_glance()
    with patch("stare.cli.utils.make_glance", return_value=g):
        result = runner.invoke(app, ["confnote", "get", "ATLAS-CONF-2024-001"])
    assert result.exit_code == 0
    assert g.confnotes.get.call_args.args[0] == "ATLAS-CONF-2024-001"


def test_confnote_get_json_output() -> None:
    g = _mock_glance()
    with patch("stare.cli.utils.make_glance", return_value=g):
        result = runner.invoke(
            app, ["confnote", "get", "ATLAS-CONF-2024-001", "--json"]
        )
    assert result.exit_code == 0
    assert g.confnotes.get.call_args.args[0] == "ATLAS-CONF-2024-001"


# ---------------------------------------------------------------------------
# confnote search
# ---------------------------------------------------------------------------


def test_confnote_search_default() -> None:
    with patch("stare.cli.utils.make_glance", return_value=_mock_glance()):
        result = runner.invoke(app, ["confnote", "search"])
    assert result.exit_code == 0
    assert "ATLAS-CONF-2024-001" in result.output


def test_confnote_search_json_output() -> None:
    with patch("stare.cli.utils.make_glance", return_value=_mock_glance()):
        result = runner.invoke(app, ["confnote", "search", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "numberOfResults" in data


def test_confnote_search_with_query() -> None:
    g = _mock_glance()
    with patch("stare.cli.utils.make_glance", return_value=g):
        result = runner.invoke(app, ["confnote", "search", "--query", "test"])
    assert result.exit_code == 0
    call_kwargs = g.confnotes.search.call_args.kwargs
    assert call_kwargs["query"] == "test"


# ---------------------------------------------------------------------------
# pubnote get
# ---------------------------------------------------------------------------


def test_pubnote_get_command() -> None:
    with patch("stare.cli.utils.make_glance", return_value=_mock_glance()):
        result = runner.invoke(app, ["pubnote", "get", "ATL-PHYS-PUB-2024-01"])
    assert result.exit_code == 0
    assert "ATL-PHYS-PUB-2024-01" in result.output


def test_pubnote_get_json_output() -> None:
    with patch("stare.cli.utils.make_glance", return_value=_mock_glance()):
        result = runner.invoke(
            app, ["pubnote", "get", "ATL-PHYS-PUB-2024-01", "--json"]
        )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data.get("finalReferenceCode") == "ATL-PHYS-PUB-2024-01"


def test_pubnote_get_not_found() -> None:
    g = _mock_glance()
    g.pubnotes.get.side_effect = NotFoundError(404, "Not Found", "No such pub note")
    with patch("stare.cli.utils.make_glance", return_value=g):
        result = runner.invoke(app, ["pubnote", "get", "MISSING"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# pubnote search
# ---------------------------------------------------------------------------


def test_pubnote_search_default() -> None:
    with patch("stare.cli.utils.make_glance", return_value=_mock_glance()):
        result = runner.invoke(app, ["pubnote", "search"])
    assert result.exit_code == 0
    assert "ATL-PHYS-PUB-2024-01" in result.output


def test_pubnote_search_json_output() -> None:
    with patch("stare.cli.utils.make_glance", return_value=_mock_glance()):
        result = runner.invoke(app, ["pubnote", "search", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "numberOfResults" in data


def test_pubnote_search_with_query() -> None:
    g = _mock_glance()
    with patch("stare.cli.utils.make_glance", return_value=g):
        result = runner.invoke(app, ["pubnote", "search", "--query", "test"])
    assert result.exit_code == 0
    call_kwargs = g.pubnotes.search.call_args.kwargs
    assert call_kwargs["query"] == "test"


# ---------------------------------------------------------------------------
# publications search
# ---------------------------------------------------------------------------


def test_publications_search_command() -> None:
    with patch("stare.cli.utils.make_glance", return_value=_mock_glance()):
        result = runner.invoke(app, ["publications", "search"])
    assert result.exit_code == 0
    assert "HDBS-2024-01" in result.output


def test_publications_search_json() -> None:
    with patch("stare.cli.utils.make_glance", return_value=_mock_glance()):
        result = runner.invoke(app, ["publications", "search", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)


def test_publications_search_with_type_filter() -> None:
    g = _mock_glance()
    with patch("stare.cli.utils.make_glance", return_value=g):
        runner.invoke(app, ["publications", "search", "--type", "Paper"])
    call_kwargs = g.publications.search.call_args.kwargs
    assert "Paper" in call_kwargs.get("types", [])


# ---------------------------------------------------------------------------
# groups / subgroups
# ---------------------------------------------------------------------------


def test_groups_command() -> None:
    with patch("stare.cli.utils.make_glance", return_value=_mock_glance()):
        result = runner.invoke(app, ["groups"])
    assert result.exit_code == 0
    assert "HDBS" in result.output


def test_groups_json_output() -> None:
    with patch("stare.cli.utils.make_glance", return_value=_mock_glance()):
        result = runner.invoke(app, ["groups", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "HDBS" in data


def test_subgroups_command() -> None:
    with patch("stare.cli.utils.make_glance", return_value=_mock_glance()):
        result = runner.invoke(app, ["subgroups"])
    assert result.exit_code == 0
    assert "Higgs" in result.output


# ---------------------------------------------------------------------------
# triggers search
# ---------------------------------------------------------------------------


def test_triggers_search_command() -> None:
    with patch("stare.cli.utils.make_glance", return_value=_mock_glance()):
        result = runner.invoke(app, ["triggers", "search"])
    assert result.exit_code == 0
    assert "HLT_e60" in result.output


def test_triggers_search_json() -> None:
    with patch("stare.cli.utils.make_glance", return_value=_mock_glance()):
        result = runner.invoke(app, ["triggers", "search", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)


def test_triggers_search_with_category_filter() -> None:
    g = _mock_glance()
    with patch("stare.cli.utils.make_glance", return_value=g):
        runner.invoke(app, ["triggers", "search", "--category", "electron"])
    call_kwargs = g.triggers.search.call_args.kwargs
    assert "electron" in call_kwargs.get("categories", [])


# ---------------------------------------------------------------------------
# TTY auto-detection
# ---------------------------------------------------------------------------


def test_auto_detect_non_tty_emits_json() -> None:
    """CliRunner captures stdout (not a TTY) → JSON emitted without --json."""
    with patch("stare.cli.utils.make_glance", return_value=_mock_glance()):
        result = runner.invoke(app, ["analysis", "search"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "numberOfResults" in data


def test_no_json_forces_rich_table() -> None:
    """--no-json overrides auto-detect and renders a Rich table."""
    with patch("stare.cli.utils.make_glance", return_value=_mock_glance()):
        result = runner.invoke(app, ["analysis", "search", "--no-json"])
    assert result.exit_code == 0
    # Rich table output is not valid JSON
    try:
        json.loads(result.output)
        is_json = True
    except json.JSONDecodeError:
        is_json = False
    assert not is_json
    assert "ANA-TEST-2024-01" in result.output


def test_no_json_paper_search_forces_rich_table() -> None:
    """--no-json on paper search renders a Rich table."""
    with patch("stare.cli.utils.make_glance", return_value=_mock_glance()):
        result = runner.invoke(app, ["paper", "search", "--no-json"])
    assert result.exit_code == 0
    try:
        json.loads(result.output)
        is_json = True
    except json.JSONDecodeError:
        is_json = False
    assert not is_json
    assert "HDBS-2024-01" in result.output


# ---------------------------------------------------------------------------
# ResponseParseError — snippet panels in handle_error
# ---------------------------------------------------------------------------


def _make_parse_error(
    *,
    loc_str: str = "results",
    snippet: object = None,
    raw_data: object = None,
) -> ResponseParseError:
    """Build a ResponseParseError with one enriched detail for testing."""
    detail = EnrichedErrorResponse(
        loc=("results",),
        loc_str=loc_str,
        message="list type expected",
        snippet=snippet,
    )
    return ResponseParseError(
        f"Failed to parse AnalysisSearchResult (1 validation error):\n  1. {loc_str}: list type expected",
        raw_data=raw_data,
        details=[detail],
    )


def test_analysis_search_prints_snippet_panel_on_parse_error() -> None:
    """handle_error renders a JSON snippet panel for each enriched detail."""
    bad_snippet = {"results": "not-a-list"}
    exc = _make_parse_error(snippet=bad_snippet)
    mock_g = _mock_glance()
    mock_g.analyses.search.side_effect = exc
    with patch("stare.cli.utils.make_glance", return_value=mock_g):
        result = runner.invoke(app, ["analysis", "search", "--no-json"])
    assert result.exit_code == 1
    assert "Error:" in result.output
    assert "validation error" in result.output.lower()
    # snippet panel title contains the loc_str
    assert "results" in result.output
    # snippet body contains the bad value
    assert "not-a-list" in result.output
    # raw-response panel not shown without verbose
    assert "Raw API Response" not in result.output


def test_analysis_search_verbose_includes_raw_panel() -> None:
    """With --verbose, a Raw API Response panel is emitted when raw_data is set."""
    bad_snippet = {"results": "not-a-list"}
    exc = _make_parse_error(snippet=bad_snippet, raw_data={"results": "not-a-list"})
    mock_g = _mock_glance()
    mock_g.analyses.search.side_effect = exc
    with patch("stare.cli.utils.make_glance", return_value=mock_g):
        result = runner.invoke(app, ["analysis", "search", "--verbose", "--no-json"])
    assert result.exit_code == 1
    assert "Raw API Response" in result.output


def test_analysis_search_passes_verbose_to_client() -> None:
    """--verbose is forwarded as verbose=True to the resource search call."""
    mock_g = _mock_glance()
    with patch("stare.cli.utils.make_glance", return_value=mock_g):
        runner.invoke(app, ["analysis", "search", "--verbose"])
    assert mock_g.analyses.search.call_args.kwargs.get("verbose") is True


def test_analysis_search_skips_snippet_panel_when_snippet_is_none() -> None:
    """When detail.snippet is None, no panel is emitted for that detail."""
    exc = _make_parse_error(snippet=None)
    mock_g = _mock_glance()
    mock_g.analyses.search.side_effect = exc
    with patch("stare.cli.utils.make_glance", return_value=mock_g):
        result = runner.invoke(app, ["analysis", "search", "--no-json"])
    assert result.exit_code == 1
    assert "Error:" in result.output
    assert "Raw API Response" not in result.output

"""Live integration tests for session inspection and export against CERN Keycloak.

Requires a stored CERN SSO session — run ``stare auth login`` (or
``stare auth login --offline``) first. Skipped by default; run with
``pixi run test-slow`` or ``pytest --runslow``.

These tests never modify the stored session: they do not import tokens,
refresh through ``import_refresh_token``, or export with ``move=True``,
because Keycloak rotates refresh tokens and a redeemed copy could
invalidate the developer's real session.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

from stare.auth import TokenManager
from stare.cli import app
from stare.exceptions import AuthenticationError

if TYPE_CHECKING:
    from stare.models.auth import SessionInfo

runner = CliRunner()


@pytest.fixture(scope="module")
def live_session() -> SessionInfo:
    info = TokenManager().get_session_info()
    if info is None:
        pytest.fail("No stored session. Run `stare auth login` first.")
    return info


@pytest.mark.slow
class TestLiveKeycloakSessionInfo:
    def test_refresh_token_decodes_to_session_info(
        self, live_session: SessionInfo
    ) -> None:
        assert isinstance(live_session.offline, bool)

    def test_offline_tokens_have_no_exp_and_online_tokens_do(
        self, live_session: SessionInfo
    ) -> None:
        """Keycloak omits ``exp`` on offline refresh tokens and sets it on
        online ones; the Session row in ``auth info`` relies on this."""
        assert live_session.offline == (live_session.refresh_expires_at is None)

    def test_auth_info_cli_shows_session_row(self, live_session: SessionInfo) -> None:
        result = runner.invoke(app, ["auth", "info"])
        assert result.exit_code == 0
        assert "Session" in result.output
        assert ("offline" if live_session.offline else "online") in result.output


@pytest.mark.slow
class TestLiveRefreshTokenExport:
    def test_export_matches_session_type_and_keeps_local_copy(
        self, live_session: SessionInfo
    ) -> None:
        manager = TokenManager()
        if not live_session.offline:
            with pytest.raises(AuthenticationError, match="not an offline session"):
                manager.export_refresh_token()
            return
        exported = manager.export_refresh_token()
        assert exported
        # Exporting without move must leave the session usable on this host.
        assert manager.get_session_info() == live_session
        assert manager.get_token()

"""Tests for the URL builder functions in stare.urls."""

from __future__ import annotations

from stare.urls import analysis_url, conf_note_url, paper_url, pub_note_url

_BASE = "https://atlas-glance.cern.ch/atlas/analysis"
_STAGING = "https://glance-staging01.cern.ch/atlas/analysis"


class TestAnalysisUrl:
    def test_default_base(self) -> None:
        url = analysis_url("ANA-HION-2018-01", web_base=_BASE)
        assert url == f"{_BASE}/analyses/details.php?ref_code=ANA-HION-2018-01"

    def test_staging_base(self) -> None:
        url = analysis_url("ANA-SUSY-2020-01", web_base=_STAGING)
        assert url == f"{_STAGING}/analyses/details.php?ref_code=ANA-SUSY-2020-01"

    def test_ref_code_preserved(self) -> None:
        ref = "ANA-HDBS-2022-99"
        assert ref in analysis_url(ref, web_base=_BASE)


class TestPaperUrl:
    def test_default_base(self) -> None:
        url = paper_url("HDBS-2018-33", web_base=_BASE)
        assert url == f"{_BASE}/papers/details.php?ref_code=HDBS-2018-33"

    def test_ref_code_preserved(self) -> None:
        ref = "EXOT-2020-01"
        assert ref in paper_url(ref, web_base=_BASE)


class TestConfNoteUrl:
    def test_default_base(self) -> None:
        url = conf_note_url("ATLAS-CONF-2023-01", web_base=_BASE)
        assert url == f"{_BASE}/confnotes/details?ref_code=ATLAS-CONF-2023-01"

    def test_ref_code_preserved(self) -> None:
        ref = "ATLAS-CONF-2022-005"
        assert ref in conf_note_url(ref, web_base=_BASE)


class TestPubNoteUrl:
    def test_default_base(self) -> None:
        url = pub_note_url("ATL-PHYS-PUB-2023-010", web_base=_BASE)
        assert url == f"{_BASE}/pubnotes/details?ref_code=ATL-PHYS-PUB-2023-010"

    def test_ref_code_preserved(self) -> None:
        ref = "ATL-PHYS-PUB-2022-01"
        assert ref in pub_note_url(ref, web_base=_BASE)


class TestUrlsCustomBase:
    def test_trailing_slash_not_added(self) -> None:
        base = "https://example.com/atlas"
        url = analysis_url("ANA-X", web_base=base)
        assert url == f"{base}/analyses/details.php?ref_code=ANA-X"

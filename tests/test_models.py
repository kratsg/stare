"""Tests for all stare pydantic models."""

from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path

import pytest
from rich.console import Console
from rich.panel import Panel

from stare.exceptions import ResponseParseError
from stare.models.analysis import Analysis, AnalysisPhase0
from stare.models.common import (
    AmiGlanceLink,
    AnalysisFramework,
    AnalysisTeam,
    Collision,
    Collisions,
    Documentation,
    EditorialBoard,
    EditorialBoardMember,
    Group,
    Groups,
    Link,
    Meeting,
    Metadata,
    Person,
    RelatedPublication,
    TeamMember,
    _extract_context,
)
from stare.models.confnote import ConfNote, ConfNotePhase1
from stare.models.enums import ConfnotePhase1State, MeetingType
from stare.models.errors import ApiErrorResponse
from stare.models.paper import Paper, PaperPhase1, PaperPhase2, PublicationPhase
from stare.models.pubnote import PubNote, PubNotePhase1, Readers
from stare.models.search import (
    AnalysisSearchResult,
    ConfNoteSearchResult,
    PaperSearchResult,
    PublicationRef,
    PubNoteSearchResult,
    Trigger,
)

# ---------------------------------------------------------------------------
# Common models
# ---------------------------------------------------------------------------


class TestPerson:
    def test_basic_parse(self) -> None:
        p = Person.model_validate(
            {
                "cernCcid": "gstark",
                "firstName": "Giordon",
                "lastName": "Stark",
                "email": "g@cern.ch",
            }
        )
        assert p.cern_ccid == "gstark"
        assert p.first_name == "Giordon"
        assert p.last_name == "Stark"
        assert p.email == "g@cern.ch"

    def test_optional_fields_default_none(self) -> None:
        p = Person.model_validate({})
        assert p.cern_ccid is None
        assert p.email is None

    def test_round_trip(self) -> None:
        data = {
            "cernCcid": "abc",
            "firstName": "A",
            "lastName": "B",
            "email": "a@b.com",
        }
        p = Person.model_validate(data)
        dumped = p.model_dump(by_alias=True, exclude_none=True)
        assert dumped["cernCcid"] == "abc"


class TestTeamMember:
    def test_inherits_person(self) -> None:
        m = TeamMember.model_validate(
            {
                "cernCcid": "x",
                "firstName": "X",
                "lastName": "Y",
                "email": "x@y.com",
                "isContactEditor": True,
                "isAnalysisContact": False,
            }
        )
        assert m.cern_ccid == "x"
        assert m.is_contact_editor is True

    def test_is_contact_editor_required(self) -> None:
        with pytest.raises(ResponseParseError):
            TeamMember.model_validate({})

    def test_is_analysis_contact_required(self) -> None:
        with pytest.raises(ResponseParseError):
            TeamMember.model_validate({"isContactEditor": True})


class TestEditorialBoardMember:
    def test_parse(self) -> None:
        m = EditorialBoardMember.model_validate(
            {
                "cernCcid": "abc",
                "firstName": "A",
                "lastName": "B",
                "email": "a@b.com",
                "isChair": True,
                "isExOfficio": False,
            }
        )
        assert m.is_chair is True
        assert m.is_ex_officio is False

    def test_required_flags(self) -> None:
        with pytest.raises(ResponseParseError):
            EditorialBoardMember.model_validate({})


class TestGroups:
    def test_parse(self) -> None:
        g = Groups.model_validate(
            {
                "leadingGroup": {"name": "SUSY"},
                "subgroups": [{"name": "Run2"}],
                "otherGroups": [],
            }
        )
        assert g.leading_group is not None
        assert g.leading_group.name == "SUSY"
        assert g.subgroups[0].name == "Run2"
        assert g.other_groups == []

    def test_all_optional(self) -> None:
        g = Groups.model_validate({})
        assert g.leading_group is None

    def test_group_name_required(self) -> None:
        with pytest.raises(ResponseParseError):
            Group.model_validate({})


class TestCollision:
    def test_parse(self) -> None:
        c = Collision.model_validate(
            {
                "type": "p-p",
                "year": "2018",
                "run": "2",
                "ecmValue": "13",
                "ecmUnit": "TeV",
                "luminosityValue": "139",
                "luminosityUnit": "fb-1",
            }
        )
        assert c.type == "p-p"
        assert c.ecm_value == "13"
        assert c.luminosity_unit == "fb-1"

    def test_luminosity_value_optional(self) -> None:
        c = Collision.model_validate(
            {
                "type": "p-p",
                "year": "2018",
                "run": "2",
                "ecmValue": "13",
                "ecmUnit": "TeV",
                "luminosityUnit": "fb-1",
            }
        )
        assert c.luminosity_value is None

    def test_required_fields(self) -> None:
        for missing in ("type", "year", "run", "ecmValue", "ecmUnit", "luminosityUnit"):
            full = {
                "type": "p-p",
                "year": "2018",
                "run": "2",
                "ecmValue": "13",
                "ecmUnit": "TeV",
                "luminosityUnit": "fb-1",
            }
            del full[missing]
            with pytest.raises(ResponseParseError):
                Collision.model_validate(full)


class TestMetadata:
    def test_parse_keywords(self) -> None:
        m = Metadata.model_validate(
            {"keywords": [{"name": "Higgs"}, {"name": "di-boson"}]}
        )
        assert m.keywords[0].name == "Higgs"
        assert m.keywords[1].name == "di-boson"

    def test_collisions(self) -> None:
        m = Metadata.model_validate(
            {
                "collisions": [
                    {
                        "type": "p-p",
                        "year": "2018",
                        "run": "2",
                        "ecmValue": "13",
                        "ecmUnit": "TeV",
                        "luminosityValue": "139",
                        "luminosityUnit": "fb-1",
                    }
                ]
            }
        )
        assert m.collisions is not None
        assert len(m.collisions) == 1
        assert m.collisions[0].type == "p-p"

    def test_optional_fields(self) -> None:
        m = Metadata.model_validate({})
        assert m.keywords == []
        assert m.statistical_tools == []
        assert m.mva_ml_tools == []


class TestDocumentation:
    def test_parse(self) -> None:
        d = Documentation.model_validate(
            {
                "repositories": [
                    {
                        "gitlabId": "123",
                        "type": "INT",
                        "url": "https://gitlab.cern.ch/r",
                    }
                ],
                "supportingInternalDocuments": [
                    {"label": "Note", "url": "https://cds.cern.ch/n"}
                ],
            }
        )
        assert d.repositories[0].gitlab_id == "123"
        assert d.supporting_internal_documents[0].label == "Note"


class TestMeeting:
    def test_parse(self) -> None:
        m = Meeting.model_validate(
            {
                "title": "EOI",
                "date": "2023-01-15",
                "comments": "ok",
                "label": "Indico",
                "url": "https://indico.cern.ch/e/1",
            }
        )
        assert m.title == "EOI"
        assert m.link is not None
        assert m.link.label == "Indico"
        assert m.link.url == "https://indico.cern.ch/e/1"

    def test_all_optional(self) -> None:
        m = Meeting.model_validate({})
        assert m.title is None
        assert m.link is None

    def test_label_only_drops_link(self) -> None:
        m = Meeting.model_validate({"title": "EOI", "label": "Indico"})
        assert m.title == "EOI"
        assert m.link is None


class TestLink:
    def test_parse(self) -> None:
        link = Link.model_validate({"label": "AMI", "url": "https://ami.cern.ch"})
        assert link.label == "AMI"
        assert link.url == "https://ami.cern.ch"

    def test_rich_with_url(self) -> None:
        link = Link.model_validate({"label": "Indico", "url": "https://indico.cern.ch"})
        console = Console(record=True, force_terminal=True, width=120)
        console.print(link)
        output = console.export_text(styles=True)
        assert "Indico" in output

    def test_url_required(self) -> None:
        with pytest.raises(ResponseParseError):
            Link.model_validate({"label": "No link"})

    def test_ami_glance_link_is_link(self) -> None:
        a = AmiGlanceLink.model_validate({"label": "AMI", "url": "https://ami.cern.ch"})
        assert isinstance(a, Link)
        assert a.label == "AMI"


class TestRelatedPublication:
    def test_parse(self) -> None:
        r = RelatedPublication.model_validate(
            {"referenceCode": "HDBS-2018-33", "type": "Paper"}
        )
        assert r.reference_code == "HDBS-2018-33"
        assert r.type == "Paper"

    def test_reference_code_optional(self) -> None:
        r = RelatedPublication.model_validate({"type": "Paper"})
        assert r.reference_code is None

    def test_type_required(self) -> None:
        with pytest.raises(ResponseParseError):
            RelatedPublication.model_validate({"referenceCode": "HDBS-2018-33"})


# ---------------------------------------------------------------------------
# Analysis models
# ---------------------------------------------------------------------------


class TestAnalysisPhase0:
    def test_parse_minimal(self) -> None:
        p = AnalysisPhase0.model_validate(
            {"state": "Phase 0 Data", "startDate": "2022-01-01"}
        )
        assert p.state == "Phase 0 Data"
        assert p.start_date == date(2022, 1, 1)

    def test_meetings_parsed(self) -> None:
        p = AnalysisPhase0.model_validate(
            {
                "eoiMeeting": [
                    {
                        "title": "EOI",
                        "date": "2022-03-01",
                        "comments": "",
                        "label": "Indico",
                        "url": "https://indico.cern.ch",
                    }
                ],
                "approvalMeeting": [],
            }
        )
        eoi = [m for m in p.meetings if m.meeting_type == MeetingType.EOI]
        approval = [m for m in p.meetings if m.meeting_type == MeetingType.APPROVAL]
        assert len(eoi) == 1
        assert eoi[0].title == "EOI"
        assert approval == []

    def test_meetings_round_trip(self) -> None:
        p = AnalysisPhase0.model_validate(
            {
                "eoiMeeting": [{"title": "EOI", "date": "2022-03-01", "comments": ""}],
                "approvalMeeting": [{"title": "Approval", "date": "2023-01-01"}],
            }
        )
        dumped = p.model_dump(by_alias=True)
        assert len(dumped["eoiMeeting"]) == 1
        assert dumped["eoiMeeting"][0]["title"] == "EOI"
        assert len(dumped["approvalMeeting"]) == 1
        assert dumped["editorialBoardRequestMeeting"] == []
        assert dumped["preApprovalMeeting"] == []

    def test_editorial_board(self) -> None:
        p = AnalysisPhase0.model_validate(
            {
                "editorialBoard": [
                    {
                        "cernCcid": "x",
                        "firstName": "A",
                        "lastName": "B",
                        "email": "a@b.com",
                        "isChair": True,
                        "isExOfficio": False,
                    }
                ]
            }
        )
        assert len(p.editorial_board) == 1
        assert p.editorial_board[0].is_chair is True

    def test_optional_fields(self) -> None:
        p = AnalysisPhase0.model_validate({})
        assert p.state is None
        assert p.meetings == []


class TestAnalysis:
    def test_minimal_parse(self) -> None:
        a = Analysis.model_validate(
            {
                "referenceCode": "ANA-HION-2018-01",
                "status": "Created",
                "shortTitle": "My analysis",
                "creationDate": "2022-01-01",
            }
        )
        assert a.reference_code == "ANA-HION-2018-01"
        assert a.status == "Created"
        assert a.short_title == "My analysis"

    def test_nested_groups(self) -> None:
        a = Analysis.model_validate(
            {
                "referenceCode": "ANA-SUSY-2020-01",
                "status": "Created",
                "groups": {
                    "leadingGroup": {"name": "SUSY"},
                    "subgroups": [],
                    "otherGroups": [],
                },
            }
        )
        assert a.groups is not None
        assert a.groups.leading_group is not None
        assert a.groups.leading_group.name == "SUSY"

    def test_nested_phase0(self) -> None:
        a = Analysis.model_validate(
            {
                "referenceCode": "ANA-X-2021-01",
                "status": "Created",
                "phase0": {"state": "Approval acceptance", "startDate": "2021-01-01"},
            }
        )
        assert a.phase0 is not None
        assert a.phase0.state == "Approval acceptance"

    def test_analysis_team(self) -> None:
        a = Analysis.model_validate(
            {
                "referenceCode": "ANA-X-2021-01",
                "status": "Created",
                "analysisTeam": [
                    {
                        "cernCcid": "u1",
                        "firstName": "A",
                        "lastName": "B",
                        "email": "a@b.com",
                        "isContactEditor": True,
                        "isAnalysisContact": False,
                    }
                ],
            }
        )
        assert len(a.analysis_team) == 1
        assert a.analysis_team[0].cern_ccid == "u1"

    def test_not_all_optional(self) -> None:
        with pytest.raises(ResponseParseError):
            Analysis.model_validate({})

    def test_extra_metadata_dict_is_preserved(self) -> None:
        a = Analysis.model_validate(
            {
                "referenceCode": "ANA-EXOT-2024-01",
                "status": "Created",
                "extraMetadata": {"key": "value"},
            }
        )
        assert a.extra_metadata == {"key": "value"}

    def test_extra_metadata_none_is_preserved(self) -> None:
        a = Analysis.model_validate(
            {"referenceCode": "ANA-EXOT-2024-01", "status": "Created"}
        )
        assert a.extra_metadata is None

    def test_extra_metadata_non_dict_coerced_with_warning(self, caplog) -> None:
        with caplog.at_level(logging.WARNING, logger="stare"):
            a = Analysis.model_validate(
                {
                    "referenceCode": "ANA-SUSY-2019-04",
                    "status": "Created",
                    "extraMetadata": "invalid JSON",
                }
            )
        assert a.extra_metadata == {}
        assert "ANA-SUSY-2019-04" in caplog.text
        assert "extraMetadata" in caplog.text

    def test_extra_metadata_non_dict_unknown_ref(self, caplog) -> None:
        with (
            caplog.at_level(logging.WARNING, logger="stare"),
            pytest.raises(ResponseParseError),
        ):
            Analysis.model_validate({"extraMetadata": 42})
        assert "<unknown>" in caplog.text

    def test_round_trip_aliases(self) -> None:
        data = {
            "referenceCode": "ANA-X-2021-01",
            "status": "Created",
            "shortTitle": "Short",
            "publicShortTitle": "Public",
        }
        a = Analysis.model_validate(data)
        dumped = a.model_dump(by_alias=True, exclude_none=True)
        assert dumped["referenceCode"] == "ANA-X-2021-01"
        assert dumped["publicShortTitle"] == "Public"


# ---------------------------------------------------------------------------
# Paper models
# ---------------------------------------------------------------------------


class TestPaperPhase1:
    def test_draft_released_date(self) -> None:
        p = PaperPhase1.model_validate({"draftReleasedDate": "2024-06-01"})
        assert p.draft_released_date is not None
        assert p.draft_released_date == date(2024, 6, 1)

    def test_all_optional(self) -> None:
        p = PaperPhase1.model_validate({})
        assert p.state is None
        assert p.draft_released_date is None


class TestPaperPhase2:
    def test_draft2_fields(self) -> None:
        p = PaperPhase2.model_validate(
            {
                "draft2ReleasedDate": "2024-07-01",
                "draft2CernSignOffDate": "2024-08-01",
                "preliminaryPlotsAndResultsReleased": True,
            }
        )
        assert p.draft2_released_date == date(2024, 7, 1)
        assert p.draft2_cern_sign_off_date == date(2024, 8, 1)
        assert p.preliminary_plots_and_results_released is True

    def test_preliminary_plots_false(self) -> None:
        p = PaperPhase2.model_validate({"preliminaryPlotsAndResultsReleased": False})
        assert p.preliminary_plots_and_results_released is False

    def test_all_optional(self) -> None:
        p = PaperPhase2.model_validate({})
        assert p.draft2_released_date is None
        assert p.draft2_cern_sign_off_date is None
        assert p.preliminary_plots_and_results_released is None


class TestPublicationPhase:
    def test_arxiv_urls(self) -> None:
        s = PublicationPhase.model_validate(
            {
                "arXivUrls": [
                    {
                        "label": "arXiv:2501.00001",
                        "url": "https://arxiv.org/abs/2501.00001",
                    }
                ]
            }
        )
        assert len(s.arxiv_urls) == 1
        assert s.arxiv_urls[0].label == "arXiv:2501.00001"

    def test_physics_briefings(self) -> None:
        s = PublicationPhase.model_validate(
            {
                "physicsBriefing": [
                    {"label": "Physics Briefing", "url": "https://atlas.cern/pb/1"}
                ]
            }
        )
        assert len(s.physics_briefing) == 1
        assert s.physics_briefing[0].label == "Physics Briefing"

    def test_final_journal_publications(self) -> None:
        s = PublicationPhase.model_validate(
            {
                "finalJournalPublication": [
                    {"label": "JHEP 01 (2025) 001", "url": "https://doi.org/10.1007/x"}
                ]
            }
        )
        assert len(s.final_journal_publication) == 1
        assert s.final_journal_publication[0].label == "JHEP 01 (2025) 001"

    def test_all_optional(self) -> None:
        s = PublicationPhase.model_validate({})
        assert s.arxiv_urls == []
        assert s.physics_briefing == []
        assert s.final_journal_publication == []


# ---------------------------------------------------------------------------
# Search / wrapper models
# ---------------------------------------------------------------------------


class TestAnalysisSearchResult:
    def test_parse(self) -> None:
        r = AnalysisSearchResult.model_validate(
            {
                "numberOfResults": 2,
                "results": [
                    {"referenceCode": "ANA-A-2021-01", "status": "Created"},
                    {"referenceCode": "ANA-B-2021-01", "status": "Closed"},
                ],
            }
        )
        assert r.number_of_results == 2
        assert len(r.results) == 2
        assert r.results[0].reference_code == "ANA-A-2021-01"
        assert r.results[1].reference_code == "ANA-B-2021-01"

    def test_empty_results(self) -> None:
        r = AnalysisSearchResult.model_validate({"numberOfResults": 0, "results": []})
        assert r.number_of_results == 0
        assert r.results == []


class TestPublicationRef:
    def test_parse(self) -> None:
        p = PublicationRef.model_validate(
            {"referenceCode": "HDBS-2018-33", "type": "Paper"}
        )
        assert p.reference_code == "HDBS-2018-33"
        assert p.type == "Paper"


class TestTrigger:
    def test_parse(self) -> None:
        t = Trigger.model_validate(
            {
                "name": "HLT_e26_lhtight",
                "category": {"name": "electron", "year": "2018"},
            }
        )
        assert t.name == "HLT_e26_lhtight"
        assert t.category is not None
        assert t.category.name == "electron"
        assert t.category.year == "2018"

    def test_no_category(self) -> None:
        t = Trigger.model_validate({"name": "HLT_mu26"})
        assert t.category is None


# ---------------------------------------------------------------------------
# Error response model
# ---------------------------------------------------------------------------


class TestApiErrorResponse:
    def test_parse_401(self) -> None:
        e = ApiErrorResponse.model_validate(
            {
                "status": 401,
                "title": "Invalid authentication token",
                "detail": "Authentication token expired or invalid",
            }
        )
        assert e.status == 401
        assert e.title == "Invalid authentication token"

    def test_parse_403(self) -> None:
        e = ApiErrorResponse.model_validate(
            {
                "status": 403,
                "title": "Action forbidden.",
                "detail": "The current action could not be performed",
            }
        )
        assert e.status == 403

    def test_optional_fields(self) -> None:
        e = ApiErrorResponse.model_validate({})
        assert e.status is None
        assert e.title is None


def test_extracting_context():
    loc_tuple = ("results", 0, "phase0", "state")
    obj = {
        "results": [
            {
                "creationDate": "2023-08-10T00:00:00+02:00",
                "referenceCode": "ANA-SUSY-2023-17",
                "status": "Analysis Closed",
                "shortTitle": "NUHM2 reinterpretation",
                "publicShortTitle": "NUHM2 reinterpretation",
                "extraMetadata": {},
                "groups": {
                    "leadingGroup": "SUSY",
                    "subgroups": ["SUSY-EW", "SUSY-Run2"],
                    "otherGroups": [],
                },
                "analysisTeam": [
                    {
                        "cernCcid": "449340",
                        "firstName": "Patrick",
                        "lastName": "Skubic",
                        "isContactEditor": True,
                    },
                    {
                        "cernCcid": "664227",
                        "firstName": "Judita",
                        "lastName": "Mamuzic",
                        "isContactEditor": True,
                    },
                ],
                "metadata": {
                    "collisions": [
                        {
                            "type": "p-p",
                            "year": "2015+2016+2017+2018",
                            "run": "Run 2",
                            "ecmValue": "13",
                            "ecmUnit": "TeV",
                            "luminosityValue": "140",
                            "luminosityUnit": "femtobarn-1",
                        }
                    ],
                    "keywords": [
                        "13 TeV",
                        "2 leptons",
                        ">=3 leptons",
                        "BSM reinterpretation",
                        "Higgsino production",
                        "MET",
                        "NUHM",
                        "R21",
                    ],
                    "mvaMlTools": [],
                    "triggers": [
                        "HLT_xe100_mht_L1XE50",
                        "HLT_xe70_mht",
                        "HLT_xe90_mht_L1XE50",
                        "HLT_xe110_pufit_L1XE50",
                        "HLT_xe110_pufit_L1XE55",
                        "HLT_xe110_pufit_xe65_L1XE50",
                        "HLT_xe110_pufit_xe70_L1XE50",
                        "HLT_xe110_mht_L1XE50",
                    ],
                },
                "amiGlance": [],
                "documentation": {
                    "repositories": [
                        {
                            "gitlabId": "167424",
                            "type": "INT",
                            "url": "https://gitlab.cern.ch/atlas-physics-office/SUSY/ANA-SUSY-2023-17/ANA-SUSY-2023-17-INT1",
                        }
                    ],
                    "supportingInternalDocuments": [],
                },
                "relatedPublications": [],
                "phase0": {
                    "state": "pub_contact_editors_definition",
                    "startDate": "2023-08-10T00:00:00+02:00",
                    "mainPhysicsAim": None,
                    "datasetUsed": None,
                    "modelTested": None,
                    "methods": None,
                    "editorialBoardFormedOn": None,
                    "pgcOrSgcSignOffDate": None,
                    "analysisContacts": [],
                },
            }
        ]
    }
    assert _extract_context(obj, loc_tuple) == "referenceCode='ANA-SUSY-2023-17'"


# ---------------------------------------------------------------------------
# PubNoteSearchResult
# ---------------------------------------------------------------------------


def test_pub_note_search_result_round_trip() -> None:
    payload = {
        "numberOfResults": 1,
        "results": [
            {
                "temporaryReferenceCode": "PUB-EXOT-2026-03",
                "finalReferenceCode": "ATL-PHYS-PUB-2024-01",
                "status": "Phase 1 Active",
                "shortTitle": "x",
            }
        ],
    }
    result = PubNoteSearchResult.model_validate(payload)
    assert result.number_of_results == 1
    assert result.results[0].final_reference_code == "ATL-PHYS-PUB-2024-01"


def test_pub_note_search_result_empty() -> None:
    result = PubNoteSearchResult.model_validate({"numberOfResults": 0, "results": []})
    assert result.number_of_results == 0
    assert result.results == []


# ---------------------------------------------------------------------------
# _ListRootModel wrappers — protocol and JSON roundtrip
# ---------------------------------------------------------------------------


class TestListRootModelWrappers:
    def test_editorial_board_protocol(self) -> None:
        eb = EditorialBoard.model_validate(
            [
                {
                    "cernCcid": "x",
                    "firstName": "A",
                    "lastName": "B",
                    "isChair": True,
                    "isExOfficio": False,
                }
            ]
        )
        assert len(eb) == 1
        assert eb[0].is_chair is True
        assert next(iter(eb)).cern_ccid == "x"
        assert bool(eb) is True
        assert bool(EditorialBoard()) is False

    def test_analysis_team_protocol(self) -> None:
        team = AnalysisTeam.model_validate(
            [
                {
                    "cernCcid": "u1",
                    "firstName": "Han",
                    "lastName": "Solo",
                    "isContactEditor": True,
                    "isAnalysisContact": False,
                }
            ]
        )
        assert len(team) == 1
        assert team[0].cern_ccid == "u1"
        assert bool(team) is True
        assert bool(AnalysisTeam()) is False

    def test_collisions_protocol(self) -> None:
        colls = Collisions.model_validate(
            [
                {
                    "type": "p-p",
                    "run": "Run 2",
                    "year": "2015-2018",
                    "ecmValue": "13",
                    "ecmUnit": "TeV",
                    "luminosityValue": "140",
                    "luminosityUnit": "fb-1",
                }
            ]
        )
        assert len(colls) == 1
        assert colls[0].run == "Run 2"
        assert bool(colls) is True
        assert bool(Collisions()) is False

    def test_readers_protocol(self) -> None:
        readers = Readers.model_validate(
            [
                {
                    "cernCcid": "r1",
                    "firstName": "Obi-Wan",
                    "lastName": "Kenobi",
                    "isFirstReader": True,
                    "isSecondReader": False,
                }
            ]
        )
        assert len(readers) == 1
        assert readers[0].first_name == "Obi-Wan"
        assert bool(readers) is True
        assert bool(Readers()) is False

    def test_wrapper_validates_from_flat_list(self) -> None:
        eb = EditorialBoard.model_validate(
            [
                {
                    "firstName": "A",
                    "lastName": "B",
                    "isChair": False,
                    "isExOfficio": False,
                }
            ]
        )
        assert isinstance(eb, EditorialBoard)
        assert isinstance(eb[0], EditorialBoardMember)

    def test_wrapper_dumps_as_flat_list(self) -> None:
        team = AnalysisTeam.model_validate(
            [
                {
                    "cernCcid": "u1",
                    "firstName": "A",
                    "lastName": "B",
                    "isContactEditor": False,
                    "isAnalysisContact": False,
                }
            ]
        )
        raw = json.loads(team.model_dump_json(by_alias=True))
        assert isinstance(raw, list), (
            "should serialize as a flat JSON array, not {root: [...]}"
        )
        assert raw[0]["cernCcid"] == "u1"

    def test_metadata_collisions_field_is_collisions_instance(self) -> None:
        m = Metadata.model_validate(
            {
                "collisions": [
                    {
                        "type": "p-p",
                        "run": "Run 2",
                        "year": "2018",
                        "ecmValue": "13",
                        "ecmUnit": "TeV",
                        "luminosityValue": "140",
                        "luminosityUnit": "fb-1",
                    }
                ]
            }
        )
        assert isinstance(m.collisions, Collisions)
        assert len(m.collisions) == 1


# ---------------------------------------------------------------------------
# __rich__ smoke tests — verify __rich__() returns a Panel without crashing
# ---------------------------------------------------------------------------


def _make_console() -> Console:
    return Console(record=True, width=120, no_color=True)


class TestRichRendering:
    def test_confnote_rich(self) -> None:
        cn = ConfNote.model_validate(
            {
                "temporaryReferenceCode": "CONF-HION-2024-01",
                "status": "Phase 1 Active",
                "shortTitle": "Heavy-ion test",
                "groups": {
                    "leadingGroup": {"name": "HION"},
                    "subgroups": [],
                    "otherGroups": [],
                },
                "metadata": {
                    "collisions": [
                        {
                            "type": "p-p",
                            "run": "Run 2",
                            "year": "2018",
                            "ecmValue": "13",
                            "ecmUnit": "TeV",
                            "luminosityValue": "140",
                            "luminosityUnit": "fb-1",
                        }
                    ],
                    "keywords": [{"name": "13 TeV"}],
                },
                "phase1": {"startDate": "2024-01-01", "releaseDate": "2024-06-01"},
                "analysisTeam": [
                    {
                        "cernCcid": "u1",
                        "firstName": "Han",
                        "lastName": "Solo",
                        "isContactEditor": True,
                        "isAnalysisContact": False,
                    }
                ],
            }
        )
        result = cn.__rich__()
        assert isinstance(result, Panel)

    def test_analysis_rich(self) -> None:
        a = Analysis.model_validate(
            {
                "referenceCode": "ANA-HION-2024-01",
                "status": "Created",
                "shortTitle": "Analysis test",
                "groups": {
                    "leadingGroup": {"name": "HION"},
                    "subgroups": [],
                    "otherGroups": [],
                },
                "metadata": {
                    "collisions": [
                        {
                            "type": "p-p",
                            "run": "Run 3",
                            "year": "2022",
                            "ecmValue": "13.6",
                            "ecmUnit": "TeV",
                            "luminosityValue": "35",
                            "luminosityUnit": "fb-1",
                        }
                    ],
                    "keywords": [{"name": "13.6 TeV"}],
                },
                "analysisTeam": [
                    {
                        "cernCcid": "u1",
                        "firstName": "Leia",
                        "lastName": "Organa",
                        "isContactEditor": False,
                        "isAnalysisContact": False,
                    }
                ],
            }
        )
        result = a.__rich__()
        assert isinstance(result, Panel)

    def test_paper_rich(self) -> None:
        p = Paper.model_validate(
            {
                "referenceCode": "HDBS-2024-01",
                "status": "Phase 1 Active",
                "shortTitle": "Paper test",
                "fullTitle": "A full title",
                "metadata": {
                    "collisions": [
                        {
                            "type": "p-p",
                            "run": "Run 2",
                            "year": "2018",
                            "ecmValue": "13",
                            "ecmUnit": "TeV",
                            "luminosityValue": "140",
                            "luminosityUnit": "fb-1",
                        }
                    ]
                },
                "analysisTeam": [
                    {
                        "cernCcid": "u2",
                        "firstName": "Luke",
                        "lastName": "Skywalker",
                        "isContactEditor": True,
                        "isAnalysisContact": False,
                    }
                ],
                "phase1": {
                    "startDate": "2024-01-01",
                    "editorialBoard": [
                        {
                            "firstName": "Yoda",
                            "lastName": "Master",
                            "isChair": False,
                            "isExOfficio": False,
                        }
                    ],
                },
            }
        )
        result = p.__rich__()
        assert isinstance(result, Panel)

    def test_pubnote_rich(self) -> None:
        pn = PubNote.model_validate(
            {
                "temporaryReferenceCode": "PUB-EXOT-2026-03",
                "status": "Phase 1 Active",
                "shortTitle": "PubNote test",
                "phase1": {
                    "startDate": "2024-03-01",
                    "readers": [
                        {
                            "firstName": "Rey",
                            "lastName": "Skywalker",
                            "isFirstReader": True,
                            "isSecondReader": False,
                        }
                    ],
                },
            }
        )
        result = pn.__rich__()
        assert isinstance(result, Panel)

    def test_publication_phase_rich_returns_none_when_empty(self) -> None:
        s = PublicationPhase.model_validate({})
        assert s.__rich__() is None

    def test_publication_phase_rich_returns_panel_when_populated(self) -> None:
        s = PublicationPhase.model_validate(
            {
                "arXivUrls": [
                    {
                        "label": "arXiv:2501.00001",
                        "url": "https://arxiv.org/abs/2501.00001",
                    }
                ],
                "finalSubmissionJournal": "JHEP",
            }
        )
        result = s.__rich__()
        assert isinstance(result, Panel)

    def test_collisions_rich_single(self) -> None:
        colls = Collisions.model_validate(
            [
                {
                    "type": "p-p",
                    "run": "Run 2",
                    "year": "2018",
                    "ecmValue": "13",
                    "ecmUnit": "TeV",
                    "luminosityValue": "140",
                    "luminosityUnit": "fb-1",
                }
            ]
        )
        result = colls.__rich__()
        assert isinstance(result, Panel)

    def test_collisions_rich_multiple(self) -> None:
        colls = Collisions.model_validate(
            [
                {
                    "type": "p-p",
                    "run": "Run 2",
                    "year": "2015-2018",
                    "ecmValue": "13",
                    "ecmUnit": "TeV",
                    "luminosityValue": "140",
                    "luminosityUnit": "fb-1",
                },
                {
                    "type": "p-p",
                    "run": "Run 3",
                    "year": "2022-2024",
                    "ecmValue": "13.6",
                    "ecmUnit": "TeV",
                    "luminosityValue": "35",
                    "luminosityUnit": "fb-1",
                },
            ]
        )
        result = colls.__rich__()
        assert isinstance(result, Panel)

    def test_rich_renders_without_crash(self) -> None:
        """End-to-end: render all four models through a real Console without errors."""
        cn = ConfNote.model_validate(
            {"temporaryReferenceCode": "CONF-HION-2024-01", "status": "Phase 1 Active"}
        )
        a = Analysis.model_validate(
            {"referenceCode": "ANA-HION-2024-01", "status": "Created"}
        )
        p = Paper.model_validate(
            {"referenceCode": "HDBS-2024-01", "status": "Phase 1 Active"}
        )
        pn = PubNote.model_validate(
            {
                "temporaryReferenceCode": "PUB-EXOT-2026-03",
                "status": "Phase 1 Active",
            }
        )

        console = _make_console()
        for model in (cn, a, p, pn):
            console.print(model)


# ---------------------------------------------------------------------------
# ConfNote models
# ---------------------------------------------------------------------------


class TestConfNote:
    def test_round_trip(self) -> None:
        payload = {
            "temporaryReferenceCode": "CONF-HION-2024-01",
            "finalReferenceCode": "ATLAS-CONF-2024-001",
            "status": "Phase 1 Finished",
            "shortTitle": "Test conf note",
        }
        note = ConfNote.model_validate(payload)
        assert note.temp_reference_code == "CONF-HION-2024-01"
        assert note.final_reference_code == "ATLAS-CONF-2024-001"
        assert note.short_title == "Test conf note"
        dumped = note.model_dump(by_alias=True, exclude_none=True)
        assert dumped["temporaryReferenceCode"] == "CONF-HION-2024-01"
        assert dumped["finalReferenceCode"] == "ATLAS-CONF-2024-001"

    def test_strict_status_rejects_unknown(self) -> None:
        with pytest.raises(ResponseParseError):
            ConfNote.model_validate(
                {
                    "temporaryReferenceCode": "CONF-HION-2024-01",
                    "status": "SomeUnknownStatus",
                }
            )

    def test_final_reference_code_optional(self) -> None:
        note = ConfNote.model_validate(
            {
                "temporaryReferenceCode": "CONF-EXOT-2024-01",
                "status": "Phase 1 Finished",
            }
        )
        assert note.temp_reference_code == "CONF-EXOT-2024-01"
        assert note.final_reference_code is None


class TestConfNotePhase1:
    def test_phase1_state_uses_confnote_enum(self) -> None:
        p = ConfNotePhase1.model_validate({"state": "Phase 1 Active"})
        assert p.state == ConfnotePhase1State.PHASE1_ACTIVE

    def test_lenient_phase1_state_accepts_unknown(self, caplog) -> None:
        with caplog.at_level(logging.WARNING, logger="stare"):
            p = ConfNotePhase1.model_validate({"state": "UnknownPhaseXYZ"})
        assert p.state == "UnknownPhaseXYZ"
        assert "UnknownPhaseXYZ" in caplog.text

    def test_all_optional(self) -> None:
        p = ConfNotePhase1.model_validate({})
        assert p.state is None


class TestConfNoteSearchResult:
    def test_round_trip(self) -> None:
        payload = {
            "numberOfResults": 1,
            "results": [
                {
                    "temporaryReferenceCode": "CONF-HION-2024-01",
                    "finalReferenceCode": "ATLAS-CONF-2024-001",
                    "status": "Phase 1 Finished",
                    "shortTitle": "x",
                }
            ],
        }
        result = ConfNoteSearchResult.model_validate(payload)
        assert result.number_of_results == 1
        assert result.results[0].final_reference_code == "ATLAS-CONF-2024-001"

    def test_empty_results(self) -> None:
        result = ConfNoteSearchResult.model_validate(
            {"numberOfResults": 0, "results": []}
        )
        assert result.number_of_results == 0
        assert result.results == []


# ---------------------------------------------------------------------------
# PubNote models
# ---------------------------------------------------------------------------


class TestPubNote:
    def test_round_trip(self) -> None:
        payload = {
            "temporaryReferenceCode": "PUB-EXOT-2026-03",
            "finalReferenceCode": "ATL-PHYS-PUB-2024-01",
            "status": "Phase 1 Active",
            "shortTitle": "Test pub note",
        }
        note = PubNote.model_validate(payload)
        assert note.temp_reference_code == "PUB-EXOT-2026-03"
        assert note.final_reference_code == "ATL-PHYS-PUB-2024-01"
        assert note.short_title == "Test pub note"
        dumped = note.model_dump(by_alias=True, exclude_none=True)
        assert dumped["temporaryReferenceCode"] == "PUB-EXOT-2026-03"
        assert dumped["finalReferenceCode"] == "ATL-PHYS-PUB-2024-01"

    def test_strict_status_rejects_unknown(self) -> None:
        with pytest.raises(ResponseParseError):
            PubNote.model_validate(
                {
                    "temporaryReferenceCode": "PUB-EXOT-2026-03",
                    "status": "SomeUnknownStatus",
                }
            )

    def test_final_reference_code_optional(self) -> None:
        note = PubNote.model_validate(
            {
                "temporaryReferenceCode": "PUB-EXOT-2026-03",
                "status": "Phase 1 Active",
            }
        )
        assert note.temp_reference_code == "PUB-EXOT-2026-03"
        assert note.final_reference_code is None

    def test_missing_temp_reference_code_raises(self) -> None:
        with pytest.raises(ResponseParseError):
            PubNote.model_validate({"finalReferenceCode": "ATL-PHYS-PUB-2024-01"})


class TestPubNotePhase1:
    def test_phase1_state_uses_confnote_enum(self) -> None:
        p = PubNotePhase1.model_validate({"state": "Phase 1 Active"})
        assert p.state == ConfnotePhase1State.PHASE1_ACTIVE

    def test_lenient_phase1_state_accepts_unknown(self, caplog) -> None:
        with caplog.at_level(logging.WARNING, logger="stare"):
            p = PubNotePhase1.model_validate({"state": "UnknownPhaseXYZ"})
        assert p.state == "UnknownPhaseXYZ"
        assert "UnknownPhaseXYZ" in caplog.text

    def test_all_optional(self) -> None:
        p = PubNotePhase1.model_validate({})
        assert p.state is None

    def test_public_web_page_url_alias(self) -> None:
        p = PubNotePhase1.model_validate(
            {"publicWebPageURLForFiguresAndTables": "https://atlas.cern/pub/x"}
        )
        assert (
            p.public_web_page_url_for_figures_and_tables == "https://atlas.cern/pub/x"
        )
        dumped = p.model_dump(by_alias=True, exclude_none=True)
        assert (
            dumped["publicWebPageURLForFiguresAndTables"] == "https://atlas.cern/pub/x"
        )


# ---------------------------------------------------------------------------
# api.yml alias alignment tests (TDD: these must fail before model fixes)
# ---------------------------------------------------------------------------


class TestPaperAliases:
    def test_arxiv_submission_date_alias(self) -> None:
        s = PublicationPhase.model_validate(
            {"arXivSubmissionDate": "2024-01-15T00:00:00+00:00"}
        )
        assert s.arxiv_submission_date is not None
        dumped = s.model_dump(by_alias=True, exclude_none=True)
        assert "arXivSubmissionDate" in dumped

    def test_first_referee_report_date_alias(self) -> None:
        s = PublicationPhase.model_validate(
            {"1stRefereeReportDate": "2024-02-01T00:00:00+00:00"}
        )
        assert s.first_referee_report_date is not None
        dumped = s.model_dump(by_alias=True, exclude_none=True)
        assert "1stRefereeReportDate" in dumped

    def test_related_analysis_alias(self) -> None:
        p = Paper.model_validate(
            {
                "referenceCode": "HDBS-2024-01",
                "status": "Phase 1 Active",
                "relatedAnalysis": {
                    "referenceCode": "ANA-HDBS-2024-01",
                    "type": "Analysis",
                },
            }
        )
        assert p.related_analysis is not None
        assert p.related_analysis.reference_code == "ANA-HDBS-2024-01"
        dumped = p.model_dump(by_alias=True, exclude_none=True)
        assert "relatedAnalysis" in dumped


class TestConfNotePhase1Alias:
    def test_public_web_page_url_alias(self) -> None:
        p = ConfNotePhase1.model_validate(
            {"publicWebPageURLForFiguresAndTables": "https://atlas.cern/conf/x"}
        )
        assert (
            p.public_web_page_url_for_figures_and_tables == "https://atlas.cern/conf/x"
        )
        dumped = p.model_dump(by_alias=True, exclude_none=True)
        assert (
            dumped["publicWebPageURLForFiguresAndTables"] == "https://atlas.cern/conf/x"
        )


class TestAnalysisFramework:
    def test_list_shape(self) -> None:
        af = AnalysisFramework.model_validate(
            {
                "ntupling": ["TopCPToolkit", "FastFrames"],
                "histogramming": ["FastFrames"],
            }
        )
        assert af.ntupling == ["TopCPToolkit", "FastFrames"]
        assert af.histogramming == ["FastFrames"]

    def test_defaults_to_empty_lists(self) -> None:
        af = AnalysisFramework.model_validate({})
        assert af.ntupling == []
        assert af.histogramming == []

    def test_null_coerced_to_empty_list(self) -> None:
        af = AnalysisFramework.model_validate({"ntupling": None, "histogramming": None})
        assert af.ntupling == []
        assert af.histogramming == []


# ---------------------------------------------------------------------------
# Real-world fixture smoke tests — one result per document type from the API
# ---------------------------------------------------------------------------

_FIXTURES = Path(__file__).parent / "fixtures"


class TestRealWorldAnalysis:
    def test_parses_without_error(self) -> None:
        data = json.loads((_FIXTURES / "analysis_search.json").read_text())
        result = AnalysisSearchResult.model_validate(data)
        assert result.number_of_results == 1
        assert len(result.results) == 1

    def test_reference_code(self) -> None:
        data = json.loads((_FIXTURES / "analysis_search.json").read_text())
        r = AnalysisSearchResult.model_validate(data).results[0]
        assert r.reference_code == "ANA-HDBS-2023-22"

    def test_analysis_team_anonymized(self) -> None:
        data = json.loads((_FIXTURES / "analysis_search.json").read_text())
        r = AnalysisSearchResult.model_validate(data).results[0]
        assert len(r.analysis_team) > 0
        member = r.analysis_team[0]
        assert member.email is not None
        assert member.email.endswith("@star.wars")

    def test_related_publications(self) -> None:
        data = json.loads((_FIXTURES / "analysis_search.json").read_text())
        r = AnalysisSearchResult.model_validate(data).results[0]
        assert r.related_publications is not None
        assert len(r.related_publications) == 1
        assert r.related_publications[0].reference_code == "CONF-HDBS-2023-22"

    def test_analysis_framework_list_fields(self) -> None:
        data = json.loads((_FIXTURES / "analysis_search.json").read_text())
        r = AnalysisSearchResult.model_validate(data).results[0]
        assert r.metadata is not None
        af = r.metadata.analysis_framework
        assert af is not None
        assert isinstance(af.ntupling, list)
        assert isinstance(af.histogramming, list)

    def test_phase0_editorial_board(self) -> None:
        data = json.loads((_FIXTURES / "analysis_search.json").read_text())
        r = AnalysisSearchResult.model_validate(data).results[0]
        assert r.phase0 is not None
        assert len(r.phase0.editorial_board) == 3


class TestRealWorldPaper:
    def test_parses_without_error(self) -> None:
        data = json.loads((_FIXTURES / "paper_search.json").read_text())
        result = PaperSearchResult.model_validate(data)
        assert result.number_of_results == 1
        assert len(result.results) == 1

    def test_reference_code(self) -> None:
        data = json.loads((_FIXTURES / "paper_search.json").read_text())
        r = PaperSearchResult.model_validate(data).results[0]
        assert r.reference_code == "IDTR-2021-01"

    def test_related_analysis_alias(self) -> None:
        # verifies the relatedAnalysis key (not associatedAnalysis) is parsed
        data = json.loads((_FIXTURES / "paper_search.json").read_text())
        r = PaperSearchResult.model_validate(data).results[0]
        assert r.related_analysis is not None
        assert r.related_analysis.reference_code == "ANA-IDTR-2021-01"

    def test_arxiv_submission_date_alias(self) -> None:
        # verifies arXivSubmissionDate (capital X) is parsed correctly
        data = json.loads((_FIXTURES / "paper_search.json").read_text())
        r = PaperSearchResult.model_validate(data).results[0]
        assert r.publication_phase is not None
        assert r.publication_phase.arxiv_submission_date is not None

    def test_analysis_team_anonymized(self) -> None:
        data = json.loads((_FIXTURES / "paper_search.json").read_text())
        r = PaperSearchResult.model_validate(data).results[0]
        assert len(r.analysis_team) > 0
        assert r.analysis_team[0].email is not None
        assert r.analysis_team[0].email.endswith("@star.wars")


class TestRealWorldConfNote:
    def test_parses_without_error(self) -> None:
        data = json.loads((_FIXTURES / "confnote_search.json").read_text())
        result = ConfNoteSearchResult.model_validate(data)
        assert result.number_of_results == 1
        assert len(result.results) == 1

    def test_reference_codes(self) -> None:
        data = json.loads((_FIXTURES / "confnote_search.json").read_text())
        r = ConfNoteSearchResult.model_validate(data).results[0]
        assert r.temp_reference_code == "CONF-SUSY-2023-04"
        assert r.final_reference_code == "ATLAS-CONF-2023-009"

    def test_public_web_page_url_alias(self) -> None:
        # verifies publicWebPageURLForFiguresAndTables (all-caps URL) is parsed
        data = json.loads((_FIXTURES / "confnote_search.json").read_text())
        r = ConfNoteSearchResult.model_validate(data).results[0]
        assert r.phase1 is not None
        assert r.phase1.public_web_page_url_for_figures_and_tables is not None
        assert (
            "ATLAS-CONF-2023-009" in r.phase1.public_web_page_url_for_figures_and_tables
        )

    def test_editorial_board_anonymized(self) -> None:
        data = json.loads((_FIXTURES / "confnote_search.json").read_text())
        r = ConfNoteSearchResult.model_validate(data).results[0]
        assert r.phase1 is not None
        assert len(r.phase1.editorial_board) == 3
        assert r.phase1.editorial_board[0].email is not None
        assert r.phase1.editorial_board[0].email.endswith("@star.wars")

    def test_draft_cds_url_anonymized(self) -> None:
        data = json.loads((_FIXTURES / "confnote_search.json").read_text())
        r = ConfNoteSearchResult.model_validate(data).results[0]
        assert r.phase1 is not None
        assert r.phase1.draft_cds_url is not None
        assert "cds.cern.ch/record/" in r.phase1.draft_cds_url


class TestRealWorldPubNote:
    def test_parses_without_error(self) -> None:
        data = json.loads((_FIXTURES / "pubnote_search.json").read_text())
        result = PubNoteSearchResult.model_validate(data)
        assert result.number_of_results == 1
        assert len(result.results) == 1

    def test_reference_code(self) -> None:
        data = json.loads((_FIXTURES / "pubnote_search.json").read_text())
        r = PubNoteSearchResult.model_validate(data).results[0]
        assert r.temp_reference_code == "PUB-SUSY-2019-05"

    def test_public_web_page_url_alias(self) -> None:
        # verifies publicWebPageURLForFiguresAndTables (all-caps URL) is parsed
        data = json.loads((_FIXTURES / "pubnote_search.json").read_text())
        r = PubNoteSearchResult.model_validate(data).results[0]
        assert r.phase1 is not None
        assert r.phase1.public_web_page_url_for_figures_and_tables is not None
        assert (
            "ATL-PHYS-PUB-2019-029"
            in r.phase1.public_web_page_url_for_figures_and_tables
        )

    def test_readers_anonymized(self) -> None:
        data = json.loads((_FIXTURES / "pubnote_search.json").read_text())
        r = PubNoteSearchResult.model_validate(data).results[0]
        assert r.phase1 is not None
        assert len(r.phase1.readers) == 2
        assert r.phase1.readers[0].email is not None
        assert r.phase1.readers[0].email.endswith("@star.wars")

    def test_analysis_team_anonymized(self) -> None:
        data = json.loads((_FIXTURES / "pubnote_search.json").read_text())
        r = PubNoteSearchResult.model_validate(data).results[0]
        assert len(r.analysis_team) > 0
        assert r.analysis_team[0].email is not None
        assert r.analysis_team[0].email.endswith("@star.wars")

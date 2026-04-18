"""Tests for all stare pydantic models."""

from __future__ import annotations

import logging
from datetime import date

from rich.console import Console

from stare.models.analysis import Analysis, AnalysisPhase0
from stare.models.common import (
    AmiGlanceLink,
    AnalysisContact,
    Collision,
    Documentation,
    EditorialBoardMember,
    Groups,
    Link,
    Meeting,
    Metadata,
    Person,
    RelatedPublication,
    TeamMember,
)
from stare.models.enums import MeetingType
from stare.models.errors import ApiErrorResponse
from stare.models.search import AnalysisSearchResult, PublicationRef, Trigger

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
                "isContactEditor": "true",
            }
        )
        assert m.cern_ccid == "x"
        assert m.is_contact_editor == "true"

    def test_is_contact_editor_optional(self) -> None:
        m = TeamMember.model_validate({})
        assert m.is_contact_editor is None


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

    def test_defaults(self) -> None:
        m = EditorialBoardMember.model_validate({})
        assert m.is_chair is None
        assert m.is_ex_officio is None


class TestAnalysisContact:
    def test_parse(self) -> None:
        c = AnalysisContact.model_validate(
            {
                "cernCcid": "abc",
                "firstName": "A",
                "lastName": "B",
                "email": "a@b.com",
                "startDate": "2023-01-01",
                "endDate": "2024-01-01",
            }
        )
        assert c.start_date == date(2023, 1, 1)
        assert c.end_date == date(2024, 1, 1)


class TestGroups:
    def test_parse(self) -> None:
        g = Groups.model_validate(
            {"leadingGroup": "SUSY", "subgroups": ["Run2"], "otherGroups": []}
        )
        assert g.leading_group == "SUSY"
        assert g.subgroups == ["Run2"]
        assert g.other_groups == []

    def test_all_optional(self) -> None:
        g = Groups.model_validate({})
        assert g.leading_group is None


class TestCollision:
    def test_parse(self) -> None:
        c = Collision.model_validate(
            {
                "type": "pp",
                "year": "2018",
                "run": "2",
                "ecmValue": "13",
                "ecmUnit": "TeV",
                "luminosityValue": "139",
                "luminosityUnit": "fb-1",
            }
        )
        assert c.type == "pp"
        assert c.ecm_value == "13"
        assert c.luminosity_unit == "fb-1"


class TestMetadata:
    def test_parse_keywords(self) -> None:
        m = Metadata.model_validate({"keywords": ["Higgs", "di-boson"]})
        assert m.keywords == ["Higgs", "di-boson"]

    def test_collisions(self) -> None:
        m = Metadata.model_validate(
            {
                "collisions": [
                    {
                        "type": "pp",
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
        assert m.collisions[0].type == "pp"

    def test_optional_fields(self) -> None:
        m = Metadata.model_validate({})
        assert m.keywords == []
        assert m.statistical_tools == []
        assert m.mva_ml_tools == []
        assert m.triggers == []
        assert m.analysis_frameworks is None
        assert m.rivet_routines == []


class TestDocumentation:
    def test_parse(self) -> None:
        d = Documentation.model_validate(
            {
                "repositories": [
                    {
                        "gitlabId": "123",
                        "type": "analysis",
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
                "linkLabel": "Indico",
                "link": "https://indico.cern.ch/e/1",
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

    def test_rich_no_url(self) -> None:
        link = Link(label="No link", url=None)
        rendered = link.__rich__()
        assert str(rendered) == "No link"

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


# ---------------------------------------------------------------------------
# Analysis models
# ---------------------------------------------------------------------------


class TestAnalysisPhase0:
    def test_parse_minimal(self) -> None:
        p = AnalysisPhase0.model_validate(
            {"state": "Active", "startDate": "2022-01-01"}
        )
        assert p.state == "Active"
        assert p.start_date == date(2022, 1, 1)

    def test_meetings_parsed(self) -> None:
        p = AnalysisPhase0.model_validate(
            {
                "eoiMeeting": [
                    {
                        "title": "EOI",
                        "date": "2022-03-01",
                        "comments": "",
                        "linkLabel": "Indico",
                        "link": "https://indico.cern.ch",
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
                "status": "Active",
                "shortTitle": "My analysis",
                "creationDate": "2022-01-01",
            }
        )
        assert a.reference_code == "ANA-HION-2018-01"
        assert a.status == "Active"
        assert a.short_title == "My analysis"

    def test_nested_groups(self) -> None:
        a = Analysis.model_validate(
            {
                "referenceCode": "ANA-SUSY-2020-01",
                "groups": {
                    "leadingGroup": "SUSY",
                    "subgroups": [],
                    "otherGroups": [],
                },
            }
        )
        assert a.groups is not None
        assert a.groups.leading_group == "SUSY"

    def test_nested_phase0(self) -> None:
        a = Analysis.model_validate(
            {
                "referenceCode": "ANA-X",
                "phase0": {"state": "Approved", "startDate": "2021-01-01"},
            }
        )
        assert a.phase0 is not None
        assert a.phase0.state == "Approved"

    def test_analysis_team(self) -> None:
        a = Analysis.model_validate(
            {
                "referenceCode": "ANA-X",
                "analysisTeam": [
                    {
                        "cernCcid": "u1",
                        "firstName": "A",
                        "lastName": "B",
                        "email": "a@b.com",
                        "isContactEditor": "true",
                    }
                ],
            }
        )
        assert len(a.analysis_team) == 1
        assert a.analysis_team[0].cern_ccid == "u1"

    def test_all_optional(self) -> None:
        a = Analysis.model_validate({})
        assert a.reference_code is None
        assert a.phase0 is None

    def test_extra_metadata_dict_is_preserved(self) -> None:
        a = Analysis.model_validate({"extraMetadata": {"key": "value"}})
        assert a.extra_metadata == {"key": "value"}

    def test_extra_metadata_none_is_preserved(self) -> None:
        a = Analysis.model_validate({})
        assert a.extra_metadata is None

    def test_extra_metadata_non_dict_coerced_with_warning(self, caplog) -> None:
        with caplog.at_level(logging.WARNING, logger="stare"):
            a = Analysis.model_validate(
                {"referenceCode": "ANA-SUSY-2019-04", "extraMetadata": "invalid JSON"}
            )
        assert a.extra_metadata == {}
        assert "ANA-SUSY-2019-04" in caplog.text
        assert "extraMetadata" in caplog.text

    def test_extra_metadata_non_dict_unknown_ref(self, caplog) -> None:
        with caplog.at_level(logging.WARNING, logger="stare"):
            a = Analysis.model_validate({"extraMetadata": 42})
        assert a.extra_metadata == {}

    def test_round_trip_aliases(self) -> None:
        data = {
            "referenceCode": "ANA-X",
            "shortTitle": "Short",
            "publicShortTitle": "Public",
        }
        a = Analysis.model_validate(data)
        dumped = a.model_dump(by_alias=True, exclude_none=True)
        assert dumped["referenceCode"] == "ANA-X"
        assert dumped["publicShortTitle"] == "Public"


# ---------------------------------------------------------------------------
# Search / wrapper models
# ---------------------------------------------------------------------------


class TestAnalysisSearchResult:
    def test_parse_totalrows_key(self) -> None:
        r = AnalysisSearchResult.model_validate(
            {
                "totalRows": 2,
                "results": [
                    {"referenceCode": "ANA-A", "status": "Active"},
                    {"referenceCode": "ANA-B", "status": "Closed"},
                ],
            }
        )
        assert r.total_rows == 2
        assert len(r.results) == 2
        assert r.results[0].reference_code == "ANA-A"

    def test_parse_numberofresults_key(self) -> None:
        r = AnalysisSearchResult.model_validate({"numberOfResults": 5, "results": []})
        assert r.total_rows == 5

    def test_empty_results(self) -> None:
        r = AnalysisSearchResult.model_validate({"totalRows": 0, "results": []})
        assert r.total_rows == 0
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

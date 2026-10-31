"""Unit tests for the value-extraction helper used by the live field tests."""

from __future__ import annotations

import pytest

from stare.models import Analysis
from tests.integration.test_live import _FieldValue, _get_nested_value


@pytest.fixture
def analysis() -> Analysis:
    return Analysis.model_validate(
        {
            "referenceCode": "ANA-TEST-2026-01",
            "creationDate": "2017-11-30",
            "status": "Phase 0 Active",
            "shortTitle": "Flow in Xe+Xe",
            "metadata": {"keywords": [{"name": "jets"}, {"name": "flow"}]},
            "phase0": {
                "eoiMeetings": [
                    {"date": "2017-12-20T00:00:00+01:00", "title": "EOI meeting"},
                    {"date": "2018-01-03T00:00:00+01:00", "title": "Follow-up"},
                ],
            },
        }
    )


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("referenceCode", _FieldValue("ANA-TEST-2026-01", in_list=False)),
        ("shortTitle", _FieldValue("Flow in Xe+Xe", in_list=False)),
        ("status", _FieldValue("Phase 0 Active", in_list=False)),
        # date and datetime fields come back in the API's JSON form
        ("creationDate", _FieldValue("2017-11-30", in_list=False)),
        (
            "phase0.eoiMeetings.date",
            _FieldValue("2017-12-20T00:00:00+01:00", in_list=True),
        ),
        # lists along the path resolve through their first element
        ("phase0.eoiMeetings.title", _FieldValue("EOI meeting", in_list=True)),
        ("metadata.keywords.name", _FieldValue("jets", in_list=True)),
    ],
)
def test_get_nested_value_returns_first_string(
    analysis: Analysis, path: str, expected: _FieldValue
) -> None:
    assert _get_nested_value(analysis, path) == expected


@pytest.mark.parametrize(
    "path",
    [
        "missing",
        "publicShortTitle",
        "phase0.missing",
        "phase0.approvalMeetings.date",
        "phase0.eoiMeetings.missing",
        "referenceCode.deeper",
    ],
)
def test_get_nested_value_returns_none_when_absent(
    analysis: Analysis, path: str
) -> None:
    assert _get_nested_value(analysis, path) is None

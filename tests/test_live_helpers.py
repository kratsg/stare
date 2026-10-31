"""Unit tests for the value-extraction helper used by the live field tests."""

from __future__ import annotations

import pytest

from stare.models import Analysis
from tests.integration.test_live import _get_nested_value


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
        ("referenceCode", "ANA-TEST-2026-01"),
        ("shortTitle", "Flow in Xe+Xe"),
        ("status", "Phase 0 Active"),
        # date and datetime fields come back in the API's JSON form
        ("creationDate", "2017-11-30"),
        ("phase0.eoiMeetings.date", "2017-12-20T00:00:00+01:00"),
        # lists along the path resolve through their first element
        ("phase0.eoiMeetings.title", "EOI meeting"),
        ("metadata.keywords.name", "jets"),
    ],
)
def test_get_nested_value_returns_first_string(
    analysis: Analysis, path: str, expected: str
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

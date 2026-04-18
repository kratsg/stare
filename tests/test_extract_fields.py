"""Tests for the OpenAPI field extractor."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from extract_dsl_fields import extract_string_fields  # noqa: E402


_MINI_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "referenceCode": {"type": "string"},
        "status": {"type": "string"},
        "creationDate": {"type": "string"},
        "groups": {
            "type": "object",
            "properties": {
                "leadingGroup": {"type": "string"},
                "subgroups": {"type": "array", "items": {"type": "string"}},
                "otherGroups": {"type": "array", "items": {"type": "string"}},
            },
        },
        "metadata": {
            "type": "object",
            "properties": {
                "keywords": {"type": "array", "items": {"type": "string"}},
                "collisions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string"},
                            "year": {"type": "string"},
                        },
                    },
                },
            },
        },
        "phase0": {
            "type": "object",
            "properties": {
                "state": {"type": "string"},
                "analysisContacts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "cernCcid": {"type": "string"},
                            "firstName": {"type": "string"},
                        },
                    },
                },
            },
        },
        "extraMetadata": {"type": "object"},
        "count": {"type": "integer"},
    },
}


def test_simple_string_included() -> None:
    fields = extract_string_fields(_MINI_SCHEMA)
    assert "referenceCode" in fields
    assert "status" in fields
    assert "creationDate" in fields


def test_nested_object_string_included() -> None:
    fields = extract_string_fields(_MINI_SCHEMA)
    assert "groups.leadingGroup" in fields


def test_array_of_strings_included() -> None:
    fields = extract_string_fields(_MINI_SCHEMA)
    assert "groups.subgroups" in fields
    assert "groups.otherGroups" in fields
    assert "metadata.keywords" in fields


def test_array_of_objects_excluded() -> None:
    fields = extract_string_fields(_MINI_SCHEMA)
    assert "metadata.collisions.type" not in fields
    assert "metadata.collisions.year" not in fields
    assert "phase0.analysisContacts.cernCcid" not in fields


def test_object_without_properties_excluded() -> None:
    fields = extract_string_fields(_MINI_SCHEMA)
    assert "extraMetadata" not in fields


def test_integer_excluded() -> None:
    fields = extract_string_fields(_MINI_SCHEMA)
    assert "count" not in fields


def test_nested_simple_string_inside_object() -> None:
    fields = extract_string_fields(_MINI_SCHEMA)
    assert "phase0.state" in fields


def test_no_array_object_children() -> None:
    fields = extract_string_fields(_MINI_SCHEMA)
    for f in fields:
        assert "analysisContacts" not in f
        assert "collisions" not in f


def test_output_is_sorted() -> None:
    fields = extract_string_fields(_MINI_SCHEMA)
    assert fields == sorted(fields)

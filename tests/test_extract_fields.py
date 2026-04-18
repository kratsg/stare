"""Tests for the OpenAPI field extractor."""

from __future__ import annotations

from typing import Any

from stare.dsl._extractor import extract_string_fields, render_fields_table

_MINI_SCHEMA: dict[str, Any] = {
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


def test_render_fields_table_header() -> None:
    table = render_fields_table(["referenceCode"])
    lines = table.strip().split("\n")
    assert lines[0] == "| Group | Fields |"
    assert lines[1] == "| ----- | ------ |"


def test_render_fields_table_top_level_only() -> None:
    table = render_fields_table(["referenceCode", "status"])
    assert "| Top-level |" in table
    assert "`referenceCode`" in table
    assert "`status`" in table


def test_render_fields_table_grouped() -> None:
    table = render_fields_table(["groups.leadingGroup", "groups.subgroups", "referenceCode"])
    assert "| Top-level |" in table
    assert "| `groups` |" in table
    assert "`referenceCode`" in table
    assert "`groups.leadingGroup`" in table


def test_render_fields_table_groups_sorted() -> None:
    table = render_fields_table(["z.field", "a.field", "top"])
    lines = table.strip().split("\n")
    assert "Top-level" in lines[2]
    assert "`a`" in lines[3]
    assert "`z`" in lines[4]


def test_render_fields_table_no_top_level() -> None:
    table = render_fields_table(["groups.leadingGroup", "phase0.state"])
    assert "Top-level" not in table
    assert "| `groups` |" in table
    assert "| `phase0` |" in table

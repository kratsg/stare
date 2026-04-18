"""Tests for the field projection DSL."""

from __future__ import annotations

from pydantic import BaseModel

from stare.models.analysis import Analysis
from stare.projection import FieldSpec, parse_specs, resolve

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _Inner(BaseModel):
    name: str | None = None
    year: str | None = None


class _Outer(BaseModel):
    ref: str | None = None
    inner: _Inner | None = None
    items: list[_Inner] = []
    tags: list[str] = []


# ---------------------------------------------------------------------------
# parse_specs
# ---------------------------------------------------------------------------


class TestParseSpecs:
    def test_single(self) -> None:
        specs = parse_specs("ref")
        assert specs == [FieldSpec(path="ref")]

    def test_multiple(self) -> None:
        specs = parse_specs("ref,inner.name")
        assert specs == [FieldSpec(path="ref"), FieldSpec(path="inner.name")]

    def test_alias(self) -> None:
        specs = parse_specs("inner.name:group")
        assert specs == [FieldSpec(path="inner.name", alias="group")]

    def test_mixed(self) -> None:
        specs = parse_specs("ref, inner.name:n, inner.year")
        assert specs[0] == FieldSpec(path="ref")
        assert specs[1] == FieldSpec(path="inner.name", alias="n")
        assert specs[2] == FieldSpec(path="inner.year")

    def test_empty_parts_skipped(self) -> None:
        specs = parse_specs("ref,,inner.name")
        assert len(specs) == 2

    def test_header_uses_alias_when_set(self) -> None:
        s = FieldSpec(path="inner.name", alias="grp")
        assert s.header == "grp"

    def test_header_falls_back_to_path(self) -> None:
        s = FieldSpec(path="inner.name")
        assert s.header == "inner.name"


# ---------------------------------------------------------------------------
# resolve — basic attribute access
# ---------------------------------------------------------------------------


class TestResolveBasic:
    def test_top_level_field(self) -> None:
        obj = _Outer(ref="ANA-X")
        assert resolve(obj, "ref") == "ANA-X"

    def test_missing_field_returns_none(self) -> None:
        obj = _Outer()
        assert resolve(obj, "ref") is None

    def test_nested_field(self) -> None:
        obj = _Outer(inner=_Inner(name="electron"))
        assert resolve(obj, "inner.name") == "electron"

    def test_nested_missing_returns_none(self) -> None:
        obj = _Outer()
        assert resolve(obj, "inner.name") is None

    def test_deeply_missing_returns_none(self) -> None:
        obj = _Outer(inner=_Inner())
        assert resolve(obj, "inner.year") is None


# ---------------------------------------------------------------------------
# resolve — list indexing
# ---------------------------------------------------------------------------


class TestResolveList:
    def test_explicit_index_zero(self) -> None:
        obj = _Outer(items=[_Inner(name="a"), _Inner(name="b")])
        assert resolve(obj, "items[0].name") == "a"

    def test_explicit_index_one(self) -> None:
        obj = _Outer(items=[_Inner(name="a"), _Inner(name="b")])
        assert resolve(obj, "items[1].name") == "b"

    def test_out_of_bounds_returns_none(self) -> None:
        obj = _Outer(items=[_Inner(name="only")])
        assert resolve(obj, "items[5].name") is None

    def test_implicit_first_element(self) -> None:
        obj = _Outer(items=[_Inner(name="first")])
        assert resolve(obj, "items.name") == "first"

    def test_implicit_first_on_empty_list_returns_none(self) -> None:
        obj = _Outer(items=[])
        assert resolve(obj, "items.name") is None

    def test_plain_string_list(self) -> None:
        obj = _Outer(tags=["foo", "bar"])
        assert resolve(obj, "tags[0]") == "foo"
        assert resolve(obj, "tags[1]") == "bar"


# ---------------------------------------------------------------------------
# resolve — dict support
# ---------------------------------------------------------------------------


class TestResolveDict:
    def test_dict_key_access(self) -> None:
        d = {"a": {"b": 42}}
        assert resolve(d, "a.b") == 42

    def test_dict_missing_key_returns_none(self) -> None:
        d = {"a": 1}
        assert resolve(d, "b") is None


# ---------------------------------------------------------------------------
# Integration: resolve with real stare models
# ---------------------------------------------------------------------------


class TestResolveWithStareModels:
    def test_analysis_reference_code(self) -> None:
        a = Analysis.model_validate(
            {"referenceCode": "ANA-HION-2018-01", "status": "Active"}
        )
        assert resolve(a, "reference_code") == "ANA-HION-2018-01"

    def test_analysis_nested_group(self) -> None:
        a = Analysis.model_validate(
            {
                "referenceCode": "ANA-X",
                "groups": {"leadingGroup": "SUSY", "subgroups": [], "otherGroups": []},
            }
        )
        assert resolve(a, "groups.leading_group") == "SUSY"

    def test_analysis_missing_groups(self) -> None:
        a = Analysis.model_validate({"referenceCode": "ANA-X"})
        assert resolve(a, "groups.leading_group") is None

    def test_analysis_repo_url(self) -> None:
        a = Analysis.model_validate(
            {
                "referenceCode": "ANA-X",
                "documentation": {
                    "repositories": [
                        {
                            "gitlabId": "42",
                            "type": "analysis",
                            "url": "https://gl.cern.ch/r",
                        }
                    ]
                },
            }
        )
        assert resolve(a, "documentation.repositories[0].url") == "https://gl.cern.ch/r"

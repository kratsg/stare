"""Field registry for semantic validation of DSL queries."""
from __future__ import annotations

import difflib
import sys
from typing import Literal

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[no-redefine]

from importlib.resources import files

from pydantic.alias_generators import to_camel

from stare.dsl.errors import DSLValidationError

Mode = Literal["analysis", "paper"]


class FieldRegistry:
    def __init__(self, fields: frozenset[str]) -> None:
        self._fields = fields

    @classmethod
    def for_mode(cls, mode: Mode) -> FieldRegistry:
        data = files("stare.dsl.data").joinpath(f"{mode}_fields.toml").read_bytes()
        fields = tomllib.loads(data.decode())["fields"]
        return cls(frozenset(fields))

    def normalize(self, field: str) -> str:
        """Convert each dot-separated segment from snake_case to camelCase."""
        return ".".join(
            to_camel(segment) if "_" in segment else segment
            for segment in field.split(".")
        )

    def validate(self, field: str) -> None:
        """Raise DSLValidationError if the (normalized) field is not in the catalogue."""
        normalized = self.normalize(field)
        if normalized not in self._fields:
            suggestions = difflib.get_close_matches(normalized, self._fields, n=1)
            hint = f"; did you mean '{suggestions[0]}'?" if suggestions else ""
            msg = f"unknown field '{normalized}'{hint}"
            raise DSLValidationError(msg)

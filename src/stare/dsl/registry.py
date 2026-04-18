"""Field registry for semantic validation of DSL queries."""

from __future__ import annotations

import difflib
import sys
from typing import Literal

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from importlib.resources import files

from pydantic.alias_generators import to_camel

from stare.dsl.errors import DSLValidationError

Mode = Literal["analysis", "paper"]


class FieldRegistry:
    """Catalogue of valid DSL field names for a given query mode."""

    def __init__(self, fields: frozenset[str]) -> None:
        """Initialise with a pre-built frozenset of camelCase field names."""
        self._fields = fields

    @classmethod
    def for_mode(cls, mode: Mode) -> FieldRegistry:
        """Load the field catalogue for *mode* from the bundled TOML data file."""
        data = files("stare.dsl.data").joinpath("fields.toml").read_bytes()
        fields = tomllib.loads(data.decode())[mode]["fields"]
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

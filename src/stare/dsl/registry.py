"""Field registry for semantic validation of DSL queries."""

from __future__ import annotations

import difflib
import sys

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from importlib.resources import files
from typing import TYPE_CHECKING

from pydantic.alias_generators import to_camel

from stare.dsl.errors import DSLValidationError

if TYPE_CHECKING:
    from stare.typing import Mode


class FieldRegistry:
    """Catalogue of valid DSL field names for a given query mode."""

    def __init__(self, fields: frozenset[str]) -> None:
        """Initialise with a pre-built frozenset of camelCase field names."""
        self._fields = fields

    @classmethod
    def for_mode(cls, mode: Mode) -> FieldRegistry:
        """Load the field catalogue for *mode* from the bundled TOML data file."""
        data = files("stare.data").joinpath("query-fields.toml").read_text()
        fields = tomllib.loads(data)[mode]["fields"]
        return cls(frozenset(fields))

    def normalize(self, field: str) -> str:
        """Convert each dot-separated segment from snake_case to camelCase."""
        return ".".join(
            to_camel(segment) if "_" in segment else segment
            for segment in field.split(".")
        )

    def fields(self) -> list[str]:
        """Return sorted list of valid camelCase field names."""
        return sorted(self._fields)

    def validate(self, field: str) -> None:
        """Raise DSLValidationError if the (normalized) field is not in the catalogue."""
        self.validate_normalized(self.normalize(field))

    def validate_normalized(self, normalized: str) -> None:
        """Raise DSLValidationError if an already-normalized field is not in the catalogue."""
        if normalized not in self._fields:
            suggestions = difflib.get_close_matches(normalized, self._fields, n=1)
            hint = f"; did you mean '{suggestions[0]}'?" if suggestions else ""
            msg = f"unknown field '{normalized}'{hint}"
            raise DSLValidationError(msg)

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
from stare.dsl.models import Operator

if TYPE_CHECKING:
    from stare.typing import Mode

_EQ_NE_ONLY = frozenset({Operator.EQ, Operator.NE})


class FieldRegistry:
    """Catalogue of valid DSL field names for a given query mode."""

    def __init__(
        self,
        fields: frozenset[str],
        boolean_fields: frozenset[str] = frozenset(),
    ) -> None:
        """Initialise with camelCase field names and an optional boolean subset."""
        self._fields = fields
        self._boolean_fields = boolean_fields

    @classmethod
    def for_mode(cls, mode: Mode) -> FieldRegistry:
        """Load the field catalogue for *mode* from the bundled TOML data file."""
        data = files("stare.data").joinpath("query-fields.toml").read_text()
        mode_data = tomllib.loads(data)[mode]
        fields = mode_data["fields"]
        boolean_fields = mode_data.get("boolean_fields", [])
        return cls(frozenset(fields), frozenset(boolean_fields))

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

    def validate_operator(self, normalized: str, operator: Operator) -> None:
        """Raise DSLValidationError if *operator* is not valid for *normalized* field.

        Boolean fields only accept ``=`` and ``!=``; all other fields accept any operator.
        """
        if normalized in self._boolean_fields and operator not in _EQ_NE_ONLY:
            msg = (
                f"field '{normalized}' is a boolean field; "
                f"only '=' and '!=' are supported (got '{operator}')"
            )
            raise DSLValidationError(msg)

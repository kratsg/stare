"""Pydantic AST nodes for the stare query DSL."""

from __future__ import annotations

from enum import Enum
from typing import Union

from pydantic import BaseModel


class Operator(str, Enum):
    """Valid comparison operators for DSL conditions."""

    EQ = "="
    NE = "!="
    CONTAIN = "contain"
    NOT_CONTAIN = "not-contain"

    def __str__(self) -> str:
        """Return the operator value, not the enum repr."""
        return self.value


Expression = Union["Condition", "And", "Or"]

# DSL keywords and operator tokens; a bare value equal to one of these would be
# reparsed as syntax, so to_dsl() quotes it.
_RESERVED_VALUES = frozenset({"and", "or", "contain", "not-contain", "=", "!="})


class Condition(BaseModel):
    """A single field OP value predicate."""

    field: str
    operator: Operator
    value: str

    def to_dsl(self) -> str:
        r"""Serialize to DSL string.

        Raises ValueError for values that cannot be represented in the grammar's
        STRING token `(/"[^"\n\r\t\f\v]*"/)`:
        - embedded double-quotes are unsupported (escaped-quote support not yet implemented)
        - non-space whitespace (tabs, newlines, etc.) is excluded by the grammar

        Wraps the value in double quotes when it is empty, contains spaces,
        parentheses, or square brackets, or is a DSL keyword/operator token
        (which would otherwise be reparsed as syntax); emits bare otherwise.
        Fields are always emitted bare after normalization.
        """
        if '"' in self.value:
            # STRING: /"[^"\n\r\t\f\v]*"/ excludes embedded double-quotes entirely.
            msg = (
                f"to_dsl: self.value {self.value!r} contains '\"', which is not "
                "representable in a STRING token; escaped-quote support is not yet implemented"
            )
            raise ValueError(msg)
        bad_ws = next((c for c in self.value if c != " " and c.isspace()), None)
        if bad_ws is not None:
            # STRING: /"[^"\n\r\t\f\v]*"/ excludes non-space whitespace at the grammar level.
            msg = f"to_dsl: self.value {self.value!r} contains non-space whitespace {bad_ws!r}, which is not supported"
            raise ValueError(msg)
        needs_quotes = (
            self.value == ""
            or any(c in " ()[]" for c in self.value)
            or self.value.lower() in _RESERVED_VALUES
        )
        value = f'"{self.value}"' if needs_quotes else self.value
        return f"{self.field} {self.operator} {value}"


class And(BaseModel):
    """Logical conjunction of exactly two sub-expressions."""

    clauses: tuple[Expression, Expression]

    def to_dsl(self) -> str:
        """Serialize to DSL string."""
        left, right = self.clauses
        return f"{left.to_dsl()} AND {right.to_dsl()}"


class Or(BaseModel):
    """Logical disjunction of exactly two sub-expressions."""

    clauses: tuple[Expression, Expression]

    def to_dsl(self) -> str:
        """Serialize to DSL string."""
        left, right = self.clauses
        return f"{left.to_dsl()} OR {right.to_dsl()}"

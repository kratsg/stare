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


class Condition(BaseModel):
    """A single field OP value predicate."""

    field: str
    operator: Operator
    value: str

    def to_dsl(self) -> str:
        """Serialize to DSL string, quoting the value when it contains spaces or parens."""
        if '"' in self.value:
            # The grammar's string token (STRING: /"[^"]*"/) does not support embedded
            # double-quotes, so emitting a quoted string would produce invalid DSL.
            msg = (
                f"to_dsl: self.value {self.value!r} contains '\"', which is not supported "
                "in a quoted DSL string; escaped-quote support is not yet implemented"
            )
            raise ValueError(msg)
        bad_ws = next((c for c in self.value if c != " " and c.isspace()), None)
        if bad_ws is not None:
            msg = f"to_dsl: self.value {self.value!r} contains non-space whitespace {bad_ws!r}, which is not supported"
            raise ValueError(msg)
        value = (
            f'"{self.value}"'
            if self.value == "" or any(c in " ()[]" for c in self.value)
            else self.value
        )
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

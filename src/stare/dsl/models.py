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
        """Serialize to DSL string, quoting the value when it contains whitespace or parens."""
        value = (
            f'"{self.value}"' if any(c in self.value for c in ' \t()"') else self.value
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

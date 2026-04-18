"""Pydantic AST nodes for the stare query DSL."""

from __future__ import annotations

from typing import Literal, Union

from pydantic import BaseModel

Operator = Literal["=", "!=", "contain", "not-contain"]

Expression = Union["Condition", "And", "Or"]


class Condition(BaseModel):
    field: str
    operator: Operator
    value: str

    def to_dsl(self) -> str:
        return f"{self.field} {self.operator} {self.value}"


class And(BaseModel):
    clauses: list[Expression]

    def to_dsl(self) -> str:
        return " and ".join(_wrap_if_or(c) for c in self.clauses)


class Or(BaseModel):
    clauses: list[Expression]

    def to_dsl(self) -> str:
        return " or ".join(c.to_dsl() for c in self.clauses)


def _wrap_if_or(expr: Expression) -> str:
    dsl = expr.to_dsl()
    return f"({dsl})" if isinstance(expr, Or) else dsl

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
    clauses: tuple[Expression, Expression]

    def to_dsl(self) -> str:
        left, right = self.clauses
        return f"{left.to_dsl()} AND {right.to_dsl()}"


class Or(BaseModel):
    clauses: tuple[Expression, Expression]

    def to_dsl(self) -> str:
        left, right = self.clauses
        return f"{left.to_dsl()} OR {right.to_dsl()}"

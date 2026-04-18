"""Pydantic AST nodes for the stare query DSL."""
from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel

Operator = Literal["=", "!=", "contain", "not-contain"]


class Condition(BaseModel):
    field: str
    operator: Operator
    value: str

    def to_dsl(self) -> str:
        escaped = self.value.replace("\\", "\\\\").replace('"', '\\"')
        return f'{self.field} {self.operator} "{escaped}"'


class And(BaseModel):
    clauses: list[Annotated[Expression, ...]]

    def to_dsl(self) -> str:
        return " and ".join(_wrap_if_or(c) for c in self.clauses)


class Or(BaseModel):
    clauses: list[Annotated[Expression, ...]]

    def to_dsl(self) -> str:
        return " or ".join(c.to_dsl() for c in self.clauses)


Expression = Union[Condition, And, Or]

And.model_rebuild()
Or.model_rebuild()


def _wrap_if_or(expr: Expression) -> str:
    dsl = expr.to_dsl()
    return f"({dsl})" if isinstance(expr, Or) else dsl

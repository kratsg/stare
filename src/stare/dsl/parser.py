"""Lark → pydantic AST transformer and public parse_dsl() entry point."""
from __future__ import annotations

from importlib.resources import files
from typing import Literal

from lark import Lark, Token, Transformer, UnexpectedInput
from lark.exceptions import VisitError

from stare.dsl.errors import DSLSyntaxError, DSLValidationError
from stare.dsl.models import And, Condition, Expression, Or
from stare.dsl.registry import FieldRegistry, Mode

_GRAMMAR = files("stare.dsl").joinpath("grammar.lark").read_text()
_LARK = Lark(_GRAMMAR, start="expression", parser="lalr")


class _DSLTransformer(Transformer):  # type: ignore[type-arg]
    def __init__(self, registry: FieldRegistry) -> None:
        super().__init__()
        self._registry = registry

    def condition(self, items: list) -> Condition:
        field_token: Token = items[0].children[0]
        op_token: Token = items[1]
        value_token: Token = items[2].children[0]

        raw_field = str(field_token)
        normalized = self._registry.normalize(raw_field)
        self._registry.validate(raw_field)

        return Condition(
            field=normalized,
            operator=str(op_token).lower(),
            value=str(value_token),
        )

    def or_expr(self, items: list) -> Or | Expression:
        clauses = [item for item in items if not isinstance(item, Token)]
        return clauses[0] if len(clauses) == 1 else Or(clauses=clauses)

    def and_expr(self, items: list) -> And | Expression:
        clauses = [item for item in items if not isinstance(item, Token)]
        return clauses[0] if len(clauses) == 1 else And(clauses=clauses)


def parse_dsl(source: str, *, mode: Literal["analysis", "paper"]) -> Expression:
    """Parse a DSL query string and return a validated AST.

    Raises DSLSyntaxError on grammar violations and DSLValidationError on
    unknown fields.  Normalizes field names to camelCase.
    """
    try:
        tree = _LARK.parse(source)
    except UnexpectedInput as exc:
        context = exc.get_context(source)
        msg = f"Invalid query syntax near '{source[:40]}': {context}"
        raise DSLSyntaxError(msg) from exc

    registry = FieldRegistry.for_mode(mode)
    try:
        return _DSLTransformer(registry).transform(tree)
    except VisitError as exc:
        if isinstance(exc.__context__, DSLValidationError):
            raise exc.__context__ from exc
        raise

"""Lark → pydantic AST transformer and public parse_dsl() entry point."""

from __future__ import annotations

import difflib
import logging
from importlib.resources import files
from typing import Any, Literal

from lark import Lark, Transformer, UnexpectedInput
from lark.exceptions import VisitError

from stare.dsl.errors import DSLSyntaxError, DSLValidationError
from stare.dsl.models import And, Condition, Expression, Operator, Or
from stare.dsl.registry import FieldRegistry

_logger = logging.getLogger("stare")

_GRAMMAR = files("stare.dsl").joinpath("grammar.lark").read_text()
_LARK = Lark(_GRAMMAR, start="expression", parser="lalr")

_VALID_OPS = tuple(op.value for op in Operator)


class _DSLTransformer(Transformer[Any, Expression]):
    def __init__(self, registry: FieldRegistry) -> None:
        super().__init__()
        self._registry = registry

    def field(self, items: list[Any]) -> str:
        """Return the field name token as a plain string."""
        return str(items[0])

    def value(self, items: list[Any]) -> str:
        """Return the value token as a plain string."""
        return str(items[0])

    def condition(self, items: list[Any]) -> Condition:
        """Build a Condition from (field_str, op_token, value_str)."""
        raw_field: str = items[0]
        op_token = items[1]
        value: str = items[2]

        normalized = self._registry.normalize(raw_field)
        self._registry.validate_normalized(normalized)

        return Condition(
            field=normalized,
            operator=Operator(str(op_token).lower()),
            value=value,
        )

    def or_expr(self, items: list[Expression]) -> Or:
        """Build an Or node."""
        left, right = items
        return Or(clauses=(left, right))

    def and_expr(self, items: list[Expression]) -> And:
        """Build an And node."""
        left, right = items
        return And(clauses=(left, right))


def _syntax_hint(exc: UnexpectedInput, source: str) -> str | None:
    """Return a short hint string for common DSL syntax mistakes, or None."""
    expected: set[str] = getattr(exc, "expected", set())
    ops_list = ", ".join(repr(op) for op in _VALID_OPS)

    if "OP" in expected:
        return f"valid operators: {ops_list}"

    if {"_AND", "_OR"} & expected:
        prefix = source[: exc.pos_in_stream].rstrip()
        last_word = prefix.rsplit(None, 1)[-1] if prefix else ""
        close = difflib.get_close_matches(
            last_word.lower(), _VALID_OPS, n=1, cutoff=0.6
        )
        if close:
            return f"did you mean '{close[0]}' instead of '{last_word}'? valid operators: {ops_list}"
        return "to chain conditions, use AND or OR"

    return None


def parse_dsl(source: str, *, mode: Literal["analysis", "paper"]) -> Expression:
    """Parse a DSL query string and return a validated AST.

    Raises DSLSyntaxError on grammar violations and DSLValidationError on
    unknown fields.  Normalizes field names to camelCase.
    """
    try:
        tree = _LARK.parse(source)
    except UnexpectedInput as exc:
        context = exc.get_context(source)
        hint = _syntax_hint(exc, source)
        suffix = f"\nHint: {hint}" if hint else ""
        msg = f"Invalid query syntax near '{source[:40]}': {context}{suffix}"
        raise DSLSyntaxError(msg) from exc

    if "(" in source:
        _logger.warning(
            "parentheses in DSL query are not supported by the server and will be ignored"
        )

    registry = FieldRegistry.for_mode(mode)
    try:
        return _DSLTransformer(registry).transform(tree)
    except VisitError as exc:
        if isinstance(exc.orig_exc, DSLValidationError):
            raise exc.orig_exc from exc
        raise

"""Syntax-only tests for the DSL Lark grammar."""
from __future__ import annotations

import pytest
from lark import Lark, UnexpectedInput

from importlib.resources import files


@pytest.fixture
def parser() -> Lark:
    grammar = files("stare.dsl").joinpath("grammar.lark").read_text()
    return Lark(grammar, start="expression", parser="lalr")


@pytest.mark.parametrize(
    "src",
    [
        'referenceCode = "HION"',
        'keywords contain "jets"',
        'status != "ARCHIVED"',
        'referenceCode contain "ANA" AND status = "ACTIVE"',
        '(status = "ACTIVE" OR status = "PENDING") AND keywords contain "jets"',
        'a.b.c = "x"',
        'field not-contain "v"',
        'f="x"',
        'F = "x" and G = "y" or H = "z"',
        r'shortTitle = "a \"quoted\" word"',
    ],
)
def test_parses_valid(parser: Lark, src: str) -> None:
    parser.parse(src)


@pytest.mark.parametrize(
    "src",
    [
        "",
        "referenceCode",
        'referenceCode = HION',
        '= "x"',
        'field === "x"',
        'field = "x" AND',
        '(field = "x"',
        'field = "x" XOR field = "y"',
        '"referenceCode" = "HION"',
    ],
)
def test_rejects_invalid(parser: Lark, src: str) -> None:
    with pytest.raises(UnexpectedInput):
        parser.parse(src)

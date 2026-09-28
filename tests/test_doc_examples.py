"""Every DSL query shown in the docs, README, CLAUDE.md and CLI help must parse.

Examples drift as the field registry changes (e.g. ``metadata.keywords`` ->
``metadata.keywords.name``) and then fail for anyone who copies them. This
check is offline: it only runs ``parse_dsl``, so it cannot tell whether a
*value* (such as a status label) exists on the server.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from stare.dsl import DSLError, parse_dsl

if TYPE_CHECKING:
    from stare.typing import Mode

_ROOT = Path(__file__).resolve().parent.parent

# CLI resource name / Python accessor -> DSL mode
_MODE: dict[str, Mode] = {
    "analysis": "analysis",
    "analyses": "analysis",
    "paper": "paper",
    "papers": "paper",
    "confnote": "confnote",
    "confnotes": "confnote",
    "pubnote": "pubnote",
    "pubnotes": "pubnote",
    "plot": "plot",
    "plots": "plot",
    "publications": "publication",
    "leadinggroups": "leadinggroup",
    "subgroups": "subgroup",
    "triggers": "trigger",
}

# Deliberately invalid: the `--no-validate` example in docs/query-dsl.md.
_INTENTIONALLY_INVALID = {"someNewField = value"}

_CLI = re.compile(r"stare (\w+) search[^\n]*?-q '([^']+)'")
_PY = re.compile(r"""g\.(\w+)\.search\(\s*query=(?:"([^"]+)"|'([^']+)')""")

# `get` examples; a reference code always contains a digit, which skips
# placeholders such as `stare analysis get REF`.
_GET_CLI = re.compile(r"stare (\w+) get ([A-Za-z-]*\d[\w-]*)")
_GET_PY = re.compile(r"""g\.(\w+)\.get\("([^"]+)"\)""")

# CLI resource name -> Glance accessor, for `get` examples
_ACCESSOR = {
    "analysis": "analyses",
    "paper": "papers",
    "confnote": "confnotes",
    "pubnote": "pubnotes",
    "plot": "plots",
    "publications": "publications",
}

_FILES = [
    *sorted((_ROOT / "docs").glob("*.md")),
    _ROOT / "README.md",
    _ROOT / "CLAUDE.md",
    *sorted((_ROOT / "src" / "stare" / "cli").glob("*.py")),
]


def _examples() -> list[tuple[str, Mode, str]]:
    found: list[tuple[str, Mode, str]] = []
    for path in _FILES:
        text = path.read_text(encoding="utf-8")
        matches = [(m.group(1), m.group(2)) for m in _CLI.finditer(text)]
        matches += [(m.group(1), m.group(2) or m.group(3)) for m in _PY.finditer(text)]
        for resource, query in matches:
            if resource not in _MODE or query in _INTENTIONALLY_INVALID:
                continue
            found.append((str(path.relative_to(_ROOT)), _MODE[resource], query))
    return found


def _get_examples() -> list[tuple[str, str, str]]:
    """Return sorted, de-duplicated (source, accessor, ref_code) `get` examples."""
    found: set[tuple[str, str, str]] = set()
    for path in _FILES:
        text = path.read_text(encoding="utf-8")
        source = str(path.relative_to(_ROOT))
        for m in _GET_CLI.finditer(text):
            if m.group(1) in _ACCESSOR:
                found.add((source, _ACCESSOR[m.group(1)], m.group(2)))
        for m in _GET_PY.finditer(text):
            if m.group(1) in _ACCESSOR.values():
                found.add((source, m.group(1), m.group(2)))
    return sorted(found)


_EXAMPLES = _examples()
_GET_EXAMPLES = _get_examples()


def test_examples_are_found() -> None:
    """Guard against the extraction regexes silently matching nothing."""
    assert len(_EXAMPLES) >= 20
    assert len(_GET_EXAMPLES) >= 10


@pytest.mark.parametrize(
    ("source", "mode", "query"), _EXAMPLES, ids=[f"{s}:{q}" for s, _, q in _EXAMPLES]
)
def test_documented_query_is_valid(source: str, mode: Mode, query: str) -> None:
    try:
        parse_dsl(query, mode=mode)
    except DSLError as exc:
        pytest.fail(f"{source}: {query!r} is not a valid {mode} query: {exc}")

"""Shared command bodies for stare CLI resource modules.

``run_search`` and ``run_get`` factor out the boilerplate duplicated across
every resource module: JSON auto-detection, DSL/Stare error handling, the
invalid-offset guard, and JSON emission. Each resource module supplies a small
typed spec (``SearchSpec`` / ``GetSpec``) pointing at its Glance resource
accessor and a ``render`` callable for the non-JSON path — the exotic
renderers (document tables, subgroup panels, trigger styling, ...) stay local
to their modules and are simply passed in as ``render``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, TypeVar

import typer

from stare._output import stdout_is_interactive
from stare.cli import utils
from stare.dsl.errors import DSLError
from stare.exceptions import StareError

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from stare.client import Glance, _Resource
    from stare.models.common import _Base
    from stare.models.search import _SearchResultsBase

# Bound to _SearchResultsBase[Any] (not e.g. object) because the generic is
# invariant: a bound of _SearchResultsBase[object] would reject concrete
# result types like _SearchResultsBase[ConfNote].
_SearchResultT = TypeVar("_SearchResultT", bound="_SearchResultsBase[Any]")
_ItemT = TypeVar("_ItemT", bound="_Base")


@dataclass(frozen=True)
class SearchOptions:
    """The query-shaping options passed straight through to ``_Resource.search()``."""

    query: str | None
    limit: int
    offset: int
    sort_by: str | None
    sort_desc: bool
    validate_query: bool
    verbose: bool


@dataclass(frozen=True)
class SearchSpec(Generic[_SearchResultT]):
    """Per-resource wiring for ``run_search``.

    *accessor* pulls the resource accessor off a ``Glance`` client (e.g.
    ``lambda g: g.confnotes``). *render* draws the non-JSON output (a Rich
    table, panel, etc.) for the search result. *check_offset* selects whether
    the invalid-offset guard applies — the document resources (analysis,
    paper, confnote, pubnote, plot) enforce it; the others don't.
    """

    accessor: Callable[[Glance], _Resource[_SearchResultT]]
    render: Callable[[_SearchResultT], None]
    check_offset: bool = True


@dataclass(frozen=True)
class GetSpec(Generic[_ItemT]):
    """Per-resource wiring for ``run_get``.

    *accessor* takes the ``Glance`` client, ref code, and verbose flag, and
    returns the fetched item (e.g.
    ``lambda g, ref, verbose: g.confnotes.get(ref, verbose=verbose)``).
    *render* draws the non-JSON output for the fetched item.
    """

    accessor: Callable[[Glance, str, bool], _ItemT]
    render: Callable[[_ItemT], None]


def run_search(
    spec: SearchSpec[_SearchResultT],
    options: SearchOptions,
    *,
    output_json: bool | None,
    no_cache: bool,
) -> None:
    """Run a resource search command: fetch, handle errors, emit JSON or render."""
    if output_json is None:
        output_json = not stdout_is_interactive()
    g = utils.make_glance(no_cache=no_cache)
    try:
        result = spec.accessor(g).search(
            query=options.query,
            limit=options.limit,
            offset=options.offset,
            sort_by=options.sort_by,
            sort_desc=options.sort_desc,
            validate_query=options.validate_query,
            verbose=options.verbose,
        )
    except DSLError as exc:
        raise typer.BadParameter(str(exc), param_hint="--query") from exc
    except StareError as exc:
        utils.handle_error(exc)
        raise typer.Exit(1) from exc

    if spec.check_offset and (
        (result.number_of_results == 0 and options.offset > 0)
        or (result.number_of_results > 0 and options.offset >= result.number_of_results)
    ):
        typer.echo(
            f"Invalid offset: {options.offset}. Maximum allowed offset is "
            f"{max(result.number_of_results - 1, 0)} for "
            f"{result.number_of_results} total results.",
            err=True,
        )
        raise typer.Exit(2)

    if output_json:
        typer.echo(result.model_dump_json(by_alias=True))
        return

    spec.render(result)


def run_get(
    spec: GetSpec[_ItemT],
    ref_code: str,
    *,
    output_json: bool | None,
    no_cache: bool,
    verbose: bool,
) -> None:
    """Run a resource get command: fetch by ref code, handle errors, emit JSON or render."""
    if output_json is None:
        output_json = not stdout_is_interactive()
    g = utils.make_glance(no_cache=no_cache)
    try:
        result = spec.accessor(g, ref_code, verbose)
    except StareError as exc:
        utils.handle_error(exc)
        raise typer.Exit(1) from exc

    if output_json:
        typer.echo(result.model_dump_json(by_alias=True))
        return

    spec.render(result)

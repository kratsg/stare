"""Shared ``Annotated`` option-type aliases for stare CLI commands.

Options whose flags, defaults, and help text are identical across every
resource module (limit/offset/sort-desc/json/no-cache/validate/verbose) live
here so each command's real signature stays explicit while killing the
per-module duplication. ``--query``, ``--sort-by``, and the ``get`` command's
``ref_code`` argument keep resource-specific help text (e.g. field-name
examples), so they are NOT aliased here and remain defined locally in each
command module.
"""

from __future__ import annotations

from typing import Annotated

import typer

LimitOption = Annotated[
    int,
    typer.Option("--limit", "-n", help="Max results to return (server default: 50)."),
]

OffsetOption = Annotated[
    int, typer.Option("--offset", help="Result offset for pagination.")
]

SortDescOption = Annotated[bool, typer.Option("--sort-desc", help="Sort descending.")]

JsonOption = Annotated[
    bool | None,
    typer.Option(
        "--json/--no-json",
        help="Emit JSON. Default: auto (JSON when piped, Rich table when interactive).",
    ),
]

NoCacheOption = Annotated[
    bool,
    typer.Option("--no-cache", help="Bypass the HTTP cache for this invocation."),
]

ValidateOption = Annotated[
    bool,
    typer.Option(
        "--validate/--no-validate",
        help="Validate and normalize the query string (default: on).",
    ),
]

VerboseOption = Annotated[
    bool,
    typer.Option(
        "--verbose",
        "-v",
        help="Attach the full raw API response to parse errors (useful for debugging).",
    ),
]

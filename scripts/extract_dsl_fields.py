"""Extract searchable DSL fields from the OpenAPI spec and write per-endpoint TOML catalogues.

Run via: pixi run extract-fields

Searchable fields are:
- type: string leaves that are NOT inside an array-of-objects path
- type: array with items.type: string (arrays of primitive strings)
"""

from __future__ import annotations

import sys
from pathlib import Path

import tomli_w
import yaml  # type: ignore[import-untyped]

from stare.dsl._extractor import extract_string_fields, render_fields_table


def _schema_for(spec: dict, schema_name: str) -> dict:
    """Return the items schema for results[] of a named search-response schema."""
    try:
        components = spec["components"]
        schemas = components["schemas"]
        schema = schemas[schema_name]
        results = schema["properties"]["results"]
        return results["items"]
    except KeyError as exc:
        msg = (
            f"OpenAPI spec missing expected key {exc} while looking up schema "
            f"'{schema_name}' → components.schemas.{schema_name}.properties.results.items"
        )
        raise ValueError(msg) from exc
    except TypeError as exc:
        msg = f"Unexpected structure in spec for schema '{schema_name}': {exc}"
        raise ValueError(msg) from exc


def main() -> None:
    repo_root = Path(__file__).parent.parent
    api_yml = repo_root / "api.yml"

    if not api_yml.exists() or not api_yml.is_file():
        print(f"Error: API spec not found at {api_yml}", file=sys.stderr)
        sys.exit(1)

    spec: dict = yaml.safe_load(api_yml.read_text())

    out_dir = repo_root / "src" / "stare" / "dsl" / "data"
    out_dir.mkdir(parents=True, exist_ok=True)

    snippets_dir = repo_root / "snippets"
    snippets_dir.mkdir(exist_ok=True)

    catalogue: dict[str, object] = {}
    for mode, schema_name in [
        ("analysis", "SearchAnalysisResponse"),
        ("paper", "SearchPaperResponse"),
    ]:
        fields = extract_string_fields(_schema_for(spec, schema_name))
        catalogue[mode] = {"fields": fields}
        print(f"{schema_name}: {len(fields)} fields")

        snippet_path = snippets_dir / f"fields-{mode}.md"
        snippet_path.write_text(render_fields_table(fields))
        print(f"→ {snippet_path.relative_to(repo_root)}")

    out_path = out_dir / "fields.toml"
    out_path.write_bytes(tomli_w.dumps(catalogue).encode())
    print(f"→ {out_path.relative_to(repo_root)}")


if __name__ == "__main__":
    main()

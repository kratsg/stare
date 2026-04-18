"""Extract searchable DSL fields from the OpenAPI spec and write per-endpoint TOML catalogues.

Run via: pixi run extract-fields

Searchable fields are:
- type: string leaves that are NOT inside an array-of-objects path
- type: array with items.type: string (arrays of primitive strings)
"""

from __future__ import annotations

from pathlib import Path

import tomli_w
import yaml  # type: ignore[import-untyped]

from stare.dsl._extractor import extract_string_fields


def _schema_for(spec: dict, schema_name: str) -> dict:
    """Return the items schema for results[] of a named search-response schema."""
    return spec["components"]["schemas"][schema_name]["properties"]["results"]["items"]


def main() -> None:
    repo_root = Path(__file__).parent.parent
    api_yml = repo_root / "api.yml"

    spec: dict = yaml.safe_load(api_yml.read_text())

    out_dir = repo_root / "src" / "stare" / "dsl" / "data"
    out_dir.mkdir(parents=True, exist_ok=True)

    catalogue: dict[str, object] = {}
    for mode, schema_name in [
        ("analysis", "SearchAnalysisResponse"),
        ("paper", "SearchPaperResponse"),
    ]:
        fields = extract_string_fields(_schema_for(spec, schema_name))
        catalogue[mode] = {"fields": fields}
        print(f"{schema_name}: {len(fields)} fields")

    out_path = out_dir / "fields.toml"
    out_path.write_bytes(tomli_w.dumps(catalogue).encode())
    print(f"→ {out_path.relative_to(repo_root)}")


if __name__ == "__main__":
    main()

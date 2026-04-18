"""Extract searchable DSL fields from the OpenAPI spec and write per-endpoint TOML catalogues.

Run via: pixi run extract-fields

Searchable fields are:
- type: string leaves that are NOT inside an array-of-objects path
- type: array with items.type: string (arrays of primitive strings)
"""
from __future__ import annotations

from pathlib import Path


def extract_string_fields(schema: dict, _prefix: str = "") -> list[str]:
    """Recursively collect searchable field paths from an OpenAPI object schema.

    Returns a sorted list of dot-separated paths.
    """
    results: list[str] = []
    properties: dict = schema.get("properties") or {}

    for name, prop in properties.items():
        path = f"{_prefix}.{name}" if _prefix else name
        kind = prop.get("type")

        if kind == "string":
            results.append(path)
        elif kind == "array":
            items = prop.get("items", {})
            if items.get("type") == "string":
                # Array of primitive strings — searchable
                results.append(path)
            # Array of objects — skip (not searchable at sub-field level)
        elif kind == "object":
            if "properties" in prop:
                results.extend(extract_string_fields(prop, path))
            # Object without properties (e.g. extraMetadata) — skip

    return sorted(results)


def _schema_for(spec: dict, schema_name: str) -> dict:
    """Return the items schema for results[] of a named search-response schema."""
    return (
        spec["components"]["schemas"][schema_name]["properties"]["results"]["items"]
    )


def main() -> None:
    repo_root = Path(__file__).parent.parent
    api_yml = repo_root / "api.yml"

    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError as e:
        msg = "PyYAML is required to run this script: pip install PyYAML"
        raise SystemExit(msg) from e

    import tomli_w

    spec: dict = yaml.safe_load(api_yml.read_text())

    out_dir = repo_root / "src" / "stare" / "dsl" / "data"
    out_dir.mkdir(parents=True, exist_ok=True)

    for mode, schema_name in [
        ("analysis", "SearchAnalysisResponse"),
        ("paper", "SearchPaperResponse"),
    ]:
        fields = extract_string_fields(_schema_for(spec, schema_name))
        out_path = out_dir / f"{mode}_fields.toml"
        out_path.write_bytes(tomli_w.dumps({"fields": fields}).encode())
        print(f"{schema_name}: {len(fields)} fields → {out_path.relative_to(repo_root)}")


if __name__ == "__main__":
    main()

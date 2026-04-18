"""Pure functions for extracting and rendering searchable field paths from an OpenAPI schema."""

from __future__ import annotations

from typing import Any


def extract_string_fields(schema: dict[str, Any], _prefix: str = "") -> list[str]:
    """Recursively collect searchable field paths from an OpenAPI object schema.

    Returns a sorted list of dot-separated paths.

    A field is included iff it is:
    - ``type: string`` and NOT nested inside an array-of-objects path, OR
    - ``type: array`` with ``items.type: string`` (array of primitive strings).
    """
    results: list[str] = []
    properties: dict[str, Any] = schema.get("properties") or {}

    for name, prop in properties.items():
        path = f"{_prefix}.{name}" if _prefix else name
        kind = prop.get("type")

        if kind == "string":
            results.append(path)
        elif kind == "array":
            items = prop.get("items", {})
            if items.get("type") == "string":
                results.append(path)
        elif kind == "object" and "properties" in prop:
            results.extend(extract_string_fields(prop, path))

    return sorted(results)


def _group_fields(fields: list[str]) -> list[tuple[str, list[str]]]:
    groups: dict[str, list[str]] = {}
    for f in fields:
        key = f.split(".")[0] if "." in f else ""
        groups.setdefault(key, []).append(f)
    result: list[tuple[str, list[str]]] = []
    if "" in groups:
        result.append(("Top-level", groups[""]))
    for key in sorted(k for k in groups if k):
        result.append((f"`{key}`", groups[key]))
    return result


def render_fields_table(fields: list[str]) -> str:
    """Render a two-column markdown table of fields grouped by first path segment."""
    lines = ["| Group | Fields |", "| ----- | ------ |"]
    for group, group_fields in _group_fields(fields):
        cells = ", ".join(f"`{f}`" for f in group_fields)
        lines.append(f"| {group} | {cells} |")
    return "\n".join(lines) + "\n"

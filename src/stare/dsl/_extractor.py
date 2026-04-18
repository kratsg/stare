"""Pure function for extracting searchable field paths from an OpenAPI schema."""

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

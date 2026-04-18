"""Field projection DSL for stare CLI search commands.

Syntax: ``-p referenceCode,status,groups.leadingGroup``

Supported path forms:
- Dot access:        ``groups.leadingGroup``
- List index:        ``documentation.repositories[0].url``
- Column alias:      ``groups.leadingGroup:group``
- Multiple paths:    ``referenceCode,status,groups.leadingGroup``

Missing paths return ``None`` (no error).  List paths without an index default
to element ``[0]``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

_TOKEN = re.compile(r"\[(\d+)\]|([^\.\[]+)")


@dataclass(frozen=True)
class FieldSpec:
    path: str
    alias: str | None = None

    @property
    def header(self) -> str:
        return self.alias or self.path


def parse_specs(raw: str) -> list[FieldSpec]:
    """Parse a comma-separated projection string into a list of FieldSpec."""
    specs = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            path, alias = part.split(":", 1)
            specs.append(FieldSpec(path=path.strip(), alias=alias.strip()))
        else:
            specs.append(FieldSpec(path=part))
    return specs


def resolve(obj: Any, path: str) -> Any:
    """Walk ``obj`` along ``path`` and return the value, or ``None`` on miss.

    Supports dotted attribute access and ``[n]`` list indexing.  A list
    encountered without an explicit index yields element ``[0]``.
    """
    current: Any = obj
    for m in _TOKEN.finditer(path):
        index_str, name = m.group(1), m.group(2)
        if index_str is not None:
            if not isinstance(current, (list, tuple)):
                return None
            idx = int(index_str)
            if idx >= len(current):
                return None
            current = current[idx]
        else:
            if isinstance(current, BaseModel):
                current = getattr(current, name, None)
            elif isinstance(current, dict):
                current = current.get(name)
            elif isinstance(current, (list, tuple)):
                # Implicit [0] when indexing into a list by name
                if not current:
                    return None
                current = current[0]
                if isinstance(current, BaseModel):
                    current = getattr(current, name, None)
                elif isinstance(current, dict):
                    current = current.get(name)
                else:
                    return None
            else:
                return None
        if current is None:
            return None
    return current

"""Shared typing utilities for stare.

Kept minimal and import-free (only stdlib ``typing``) so every module can
consume it without creating import cycles.
"""

from __future__ import annotations

from typing import Literal

Mode = Literal["analysis", "confnote", "paper", "pubnote"]
"""Valid query-DSL / resource modes."""

__all__ = ["Mode"]

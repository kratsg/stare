"""Smoke test ensuring enums.py imports cleanly and all Lenient aliases exist."""

from __future__ import annotations

import importlib


def test_enums_module_imports_cleanly():
    import stare.models.enums as enums_mod

    importlib.reload(enums_mod)

    # Every auto-generated enum has a matching Lenient alias
    for name in (
        "LenientAnalysisPhase0State",
        "LenientPaperPhase1State",
        "LenientPaperPhase2State",
        "LenientPaperSubmissionState",
        "LenientConfnoteStatus",
        "LenientConfnotePhase1State",
    ):
        assert hasattr(enums_mod, name), f"Missing Lenient alias: {name}"

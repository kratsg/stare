"""Smoke test ensuring enums.py imports cleanly and all Lenient aliases exist."""

from __future__ import annotations

from stare.models import enums


def test_enums_module_imports_cleanly():
    # Every auto-generated enum has a matching Lenient alias
    for name in (
        "LenientAnalysisPhase0State",
        "LenientPaperPhase1State",
        "LenientPaperPhase2State",
        "LenientPaperSubmissionState",
        "LenientConfnoteStatus",
        "LenientConfnotePhase1State",
    ):
        assert hasattr(enums, name), f"Missing Lenient alias: {name}"

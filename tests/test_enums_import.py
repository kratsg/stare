"""Smoke test ensuring enums.py imports cleanly and all Lenient aliases exist."""

from __future__ import annotations

from stare.models import enums


def test_enums_module_imports_cleanly():
    # Critical API-facing enums have matching Lenient aliases
    for name in (
        "LenientAnalysisPhase0State",
        "LenientPaperPhase1State",
        "LenientPaperPhase2State",
        "LenientPaperSubmissionState",
        "LenientAnalysisStatus",
        "LenientPaperStatus",
        "LenientConfnoteStatus",
        "LenientConfnotePhase1State",
    ):
        assert hasattr(enums, name), f"Missing Lenient alias: {name}"
        assert hasattr(enums, name), f"Missing Lenient alias: {name}"

"""Output-mode detection for CLI commands.

The stare CLI renders Rich tables to terminals and structured JSON to pipes and
files, so users (and LLMs) can chain ``stare ... | jq`` without needing to set
a flag.
"""

from __future__ import annotations

import os
import stat
import sys


def stdout_is_interactive() -> bool:
    """Return True iff stdout is a TTY (not a pipe or regular file).

    Uses fstat to distinguish FIFOs and regular files from character devices;
    falls back to isatty() when fstat fails (e.g. test harnesses that replace
    sys.stdout with an in-memory buffer).
    """
    try:
        mode = os.fstat(sys.stdout.fileno()).st_mode
    except (OSError, ValueError, AttributeError):
        return sys.stdout.isatty()
    if stat.S_ISFIFO(mode) or stat.S_ISREG(mode):
        return False
    return sys.stdout.isatty()

"""URL builders for the ATLAS Glance web UI.

Functions accept a ``web_base`` parameter (usually ``StareSettings.web_base_url``)
so they remain pure and easy to test without touching settings.
"""

from __future__ import annotations


def analysis_url(ref_code: str, *, web_base: str) -> str:
    """Return the Glance web UI URL for an analysis."""
    return f"{web_base}/analyses/details.php?ref_code={ref_code}"


def paper_url(ref_code: str, *, web_base: str) -> str:
    """Return the Glance web UI URL for a paper."""
    return f"{web_base}/papers/details.php?ref_code={ref_code}"


def confnote_url(ref_code: str, *, web_base: str) -> str:
    """Return the Glance web UI URL for a CONF note."""
    return f"{web_base}/confnotes/details?ref_code={ref_code}"


def pubnote_url(ref_code: str, *, web_base: str) -> str:
    """Return the Glance web UI URL for a PUB note."""
    return f"{web_base}/pubnotes/details?ref_code={ref_code}"

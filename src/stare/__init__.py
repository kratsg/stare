"""stare — Python library and CLI for the CERN ATLAS Glance/Fence API."""

from __future__ import annotations

from stare._version import version as __version__
from stare.client import Glance

__all__ = ["Glance", "__version__"]

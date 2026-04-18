---
icon: lucide/rocket
---

# stare

**stare** is a Python library and CLI for the
[CERN ATLAS Glance/Fence API](https://atlas-glance.cern.ch/atlas/analysis/api/docs/).
It provides typed access to analyses, papers, CONF notes, PUB notes,
publications, groups, subgroups, and triggers — with OAuth2 PKCE authentication
against CERN Keycloak built in.

[![Actions Status](https://github.com/kratsg/stare/workflows/CI/badge.svg)](https://github.com/kratsg/stare/actions)
[![PyPI version](https://img.shields.io/pypi/v/stare.svg)](https://pypi.org/project/stare/)

## Quick start

=== "CLI"

    ```bash
    python -m pip install stare
    stare auth login          # opens CERN SSO in your browser
    stare analysis search --limit 10
    ```

=== "Library"

    ```python
    from stare import Glance

    with Glance() as g:
        result = g.analyses.search(query="referenceCode = ANA-HION-2018-01")
        for a in result.results:
            print(a.reference_code, a.short_title)
    ```

## Features

- **Analyses and papers** — search and retrieve ATLAS analyses, papers, CONF
  notes, and PUB notes
- **Simple query language** — filter by reference code, status, leading group,
  keywords, and more
- **Secure authentication** — browser-based CERN SSO login; no passwords stored,
  tokens refresh automatically
- **CLI and library** — Rich tables for interactive use, auto-JSON when piping;
  full Python API for scripts and notebooks

---

Ready to install? See [Getting started](getting-started.md).

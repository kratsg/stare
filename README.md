# stare

Python library and CLI for the
[CERN ATLAS Glance/Fence API](https://atlas-glance.cern.ch/atlas/analysis/api/docs/).

[![Actions Status][actions-badge]][actions-link]
[![Documentation Status][rtd-badge]][rtd-link]
[![PyPI version][pypi-version]][pypi-link]

[actions-badge]: https://github.com/kratsg/stare/workflows/CI/badge.svg
[actions-link]: https://github.com/kratsg/stare/actions
[rtd-badge]: https://readthedocs.org/projects/stare/badge/?version=latest
[rtd-link]: https://stare.readthedocs.io/en/latest/?badge=latest
[pypi-version]: https://img.shields.io/pypi/v/stare.svg
[pypi-link]: https://pypi.org/project/stare/

## Installation

```bash
pip install stare
```

## Authentication

`stare` uses PKCE (no passwords stored). Run once to authenticate:

```bash
stare login
```

Your browser will open CERN SSO. After approval, tokens are stored locally and
refreshed automatically.

## CLI usage

```bash
# Search analyses
stare search --query '"referenceCode" = "ANA-HION-2018-01"'
stare search -q '"keywords" contain "Higgs"' --limit 20

# Get individual resources (once endpoints go live)
stare analysis ANA-HION-2018-01
stare paper HDBS-2018-33

# List metadata
stare groups
stare subgroups

# Auth management
stare login
stare logout
stare auth status
```

Add `--json` to any command for machine-readable output.

## Library usage

```python
from stare import Glance

g = Glance()

# Search analyses (currently live)
result = g.analyses.search(query='"referenceCode" = "ANA-HION-2018-01"')
print(f"Found {result.total_rows} analyses")
for analysis in result.results:
    print(analysis.reference_code, analysis.short_title)

# Individual resource lookups (available as API endpoints go live)
analysis = g.analyses.get("ANA-HION-2018-01")
paper = g.papers.get("HDBS-2018-33")
groups = g.groups.list()
```

Use as a context manager for explicit connection lifecycle:

```python
with Glance() as g:
    result = g.analyses.search(query='"status" = "Active"')
```

Inject a token directly (useful in CI/automated scripts):

```python
g = Glance(token="your-access-token")
```

## Configuration

Override defaults via environment variables:

| Variable          | Default                                           |
| ----------------- | ------------------------------------------------- |
| `STARE_BASE_URL`  | `https://atlas-glance.cern.ch/atlas/analysis/api` |
| `STARE_CLIENT_ID` | `stare`                                           |
| `STARE_AUTH_URL`  | CERN Keycloak auth endpoint                       |
| `STARE_TOKEN_URL` | CERN Keycloak token endpoint                      |

## Development

```bash
git clone https://github.com/kratsg/stare
cd stare
pixi install
pixi run pre-commit-install
stare login
pixi run test
```

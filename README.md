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
python -m pip install stare
```

## Authentication

`stare` uses PKCE (no passwords stored). Run once to authenticate:

```bash
stare auth login
```

Your browser will open CERN SSO. After approval, tokens are stored locally and
refreshed automatically.

## CLI usage

```bash
# Search analyses — Rich table in terminal, JSON when piped
stare analysis search
stare analysis search --query 'referenceCode = ANA-HION-2018-01'
stare analysis search -q 'keywords contain Higgs' --limit 20

# Pipe to jq for field selection (JSON is auto-emitted)
stare analysis search | jq '.results[].referenceCode'
stare analysis search -q 'referenceCode contain HION' \
  | jq -r '.results[] | select(.status == "Active") | .referenceCode'

# Search papers
stare paper search --query 'referenceCode = HDBS-2018-33'

# Get individual resources
stare analysis get ANA-HION-2018-01
stare paper get HDBS-2018-33

# CONF notes / PUB notes
stare conf-note ATLAS-CONF-2024-001
stare pub-note ATL-PHYS-PUB-2024-001

# List metadata
stare groups
stare subgroups

# Auth management
stare auth login
stare auth logout
stare auth status

# Cache management
stare cache info
stare cache clear --yes
```

Output is a Rich table when stdout is a terminal and JSON when piped or
redirected. Use `--json` / `--no-json` to override. Commands that expose
`--no-cache` bypass the 8-hour on-disk response cache for that invocation.

## Library usage

```python
from stare import Glance

g = Glance()

# Search analyses (currently live)
result = g.analyses.search(query="referenceCode = ANA-HION-2018-01")
print(f"Found {result.total_rows} analyses")
for analysis in result.results:
    print(analysis.reference_code, analysis.short_title)

# Search papers (currently live)
paper_result = g.papers.search(query="referenceCode = HDBS-2018-33")
print(f"Found {paper_result.total_rows} papers")
for paper in paper_result.results:
    print(paper.reference_code, paper.short_title)

# Individual resource lookups (available as API endpoints go live)
analysis = g.analyses.get("ANA-HION-2018-01")
paper = g.papers.get("HDBS-2018-33")
groups = g.groups.list()
```

Use as a context manager for explicit connection lifecycle:

```python
with Glance() as g:
    result = g.analyses.search(query="status = Active")
```

Inject a token directly (useful in CI/automated scripts):

```python
g = Glance(token="your-access-token")
```

## Configuration

Override defaults via environment variables:

| Variable              | Default                                           |
| --------------------- | ------------------------------------------------- |
| `STARE_BASE_URL`      | `https://atlas-glance.cern.ch/atlas/analysis/api` |
| `STARE_CLIENT_ID`     | `stare`                                           |
| `STARE_AUTH_URL`      | CERN Keycloak auth endpoint                       |
| `STARE_TOKEN_URL`     | CERN Keycloak token endpoint                      |
| `STARE_CALLBACK_PORT` | `8182` (must match Keycloak registration)         |

## Development

```bash
git clone https://github.com/kratsg/stare
cd stare
pixi install
pixi run pre-commit-install
pixi run stare auth login
pixi run test
```

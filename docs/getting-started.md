---
icon: lucide/play
---

# Getting started

## Installation

```bash
pip install stare
```

Or with [pixi](https://prefix.dev/docs/pixi/overview):

```bash
pixi add stare
```

Requires Python 3.10 or later.

## Authentication

`stare` uses OAuth2 PKCE — no passwords are ever stored. Run once:

```bash
stare auth login
```

Your browser opens the CERN SSO login page. After you approve, tokens are stored
in your OS credential store (macOS Keychain, Linux Secret Service, or Windows
Credential Locker) and refreshed automatically.

See the [Authentication](auth.md) page for full details on token storage,
lifecycle, token exchange, and security properties.

## CLI usage

### Search analyses

```bash
# List recent analyses (default limit: 50)
stare analysis search

# Filter by a query string
stare analysis search --query '"referenceCode" = "ANA-HION-2018-01"'
stare analysis search -q '"keywords" contain "Higgs"' --limit 20

# Paginate
stare analysis search --offset 50 --limit 25

# Machine-readable output
stare analysis search --json

# Project arbitrary fields into the table columns
stare analysis search -p "reference_code,groups.leading_group,documentation.repositories[0].url"
```

### Search papers

```bash
stare paper search
stare paper search -q '"status" = "Active"' --limit 10
stare paper search --json
stare paper search -p "reference_code,status,phase1.state"
```

### Get individual resources

```bash
stare analysis get ANA-HION-2018-01
stare paper get HDBS-2018-33
stare conf-note ATLAS-CONF-2024-001
stare pub-note ATL-PHYS-PUB-2024-001
```

Add `--json` to any command for JSON output.

### Publications, groups, and triggers

```bash
# Search across all publication types
stare publications search
stare publications search --type Paper --group HDBS

# List all leading groups / subgroups
stare groups
stare subgroups

# Search triggers
stare triggers search --category electron --year 2024
```

## Library usage

```python
from stare import Glance

g = Glance()

# Search analyses
result = g.analyses.search(query='"referenceCode" = "ANA-HION-2018-01"')
print(f"Found {result.total_rows} analyses")
for analysis in result.results:
    print(analysis.reference_code, analysis.short_title)

# Search papers
paper_result = g.papers.search(query='"status" = "Active"')
for paper in paper_result.results:
    print(paper.reference_code, paper.status)

# Individual resource lookups
analysis = g.analyses.get("ANA-HION-2018-01")
paper = g.papers.get("HDBS-2018-33")
groups = g.groups.list()
```

### Context manager

Use `Glance` as a context manager to explicitly control the underlying HTTP
connection lifecycle:

```python
with Glance() as g:
    result = g.analyses.search(query='"status" = "Active"')
    for a in result.results:
        print(a.reference_code)
```

### Token injection

Inject a token directly — useful in CI pipelines where interactive login is not
available:

```python
import os
from stare import Glance

g = Glance(token=os.environ["GLANCE_TOKEN"])
result = g.analyses.search()
```

## Current API endpoint availability

| Endpoint                    | Status   |
| --------------------------- | -------- |
| `GET /searchAnalysis`       | **Live** |
| `GET /searchPaper`          | **Live** |
| `GET /analyses/{ref_code}`  | Planned  |
| `GET /papers/{ref_code}`    | Planned  |
| `GET /confnotes/{ref_code}` | Planned  |
| `GET /pubnotes/{ref_code}`  | Planned  |
| `GET /publications/search`  | Planned  |
| `GET /groups`               | Planned  |
| `GET /subgroups`            | Planned  |
| `GET /triggers/search`      | Planned  |

The client exposes the full API surface today; planned endpoints will return a
`NotFoundError` until the server rolls them out.

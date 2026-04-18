---
icon: lucide/play
---

# Getting started

## Installation

```bash
python -m pip install stare
```

Or with [pixi](https://prefix.dev/docs/prefix/overview):

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

### Search

Every resource that supports server-side search exposes a
`stare <resource> search` subcommand with a common set of flags:

| Flag                           | Short | Meaning                                       |
| ------------------------------ | ----- | --------------------------------------------- |
| `--query`                      | `-q`  | DSL filter; see [Query DSL](query-dsl.md)     |
| `--limit`                      | `-n`  | Max results returned (default: 50)            |
| `--offset`                     |       | Pagination offset                             |
| `--sort-by`                    |       | camelCase API field to sort by                |
| `--sort-desc`                  |       | Sort descending                               |
| `--json` / `--no-json`         |       | Force or suppress JSON output                 |
| `--no-cache`                   |       | Bypass the 8-hour cache for this invocation   |
| `--validate` / `--no-validate` |       | Enable/disable client-side DSL field checking |

Today `--query` applies to `stare analysis search` and `stare paper search`;
more search commands will appear as the server rolls out new endpoints.

```bash
# List recent analyses (default limit: 50)
stare analysis search
stare analysis search -q 'referenceCode = ANA-HION-2018-01'
stare analysis search -q 'keywords contain Higgs' -n 20

# Paginate
stare analysis search --offset 50 --limit 25

# Machine-readable JSON (also the default when stdout is a pipe)
stare analysis search --json

# Papers work the same way
stare paper search
stare paper search -q 'status = Active' -n 10
```

### Piping output

`stare` auto-detects when stdout is a pipe or regular file and emits JSON
instead of a Rich table, so you can chain `jq`, `grep`, `awk`, or any other UNIX
tool:

```bash
# List reference codes for active HION analyses
stare analysis search -q 'referenceCode contain HION' \
  | jq -r '.results[] | select(.status == "Active") | .referenceCode'

# Emit (ref_code, leading_group) pairs as TSV
stare analysis search \
  | jq -r '.results[] | [.referenceCode, .groups.leadingGroup] | @tsv'

# Save a full result set to disk for repeated analysis
stare analysis search -q 'referenceCode contain HION' > results.json
```

Override the auto-detection with `--json` (force JSON in a terminal) or
`--no-json` (force the Rich table when piping).

### Get individual resources

```bash
stare analysis get ANA-HION-2018-01
stare paper get HDBS-2018-33
stare conf-note ATLAS-CONF-2024-001
stare pub-note ATL-PHYS-PUB-2024-001
```

Add `--json` to any command for JSON output, or pipe to another command or file.

### Publications, groups, and triggers

```bash
# Search across all publication types (filter flags: --ref --type --group --subgroup --status)
stare publications search
stare publications search --type Paper --group HDBS
stare publications search --subgroup Boosted --status Active

# List all leading groups / subgroups
stare groups
stare subgroups

# Search triggers
stare triggers search --category electron --year 2024
```

These commands return `NotFoundError` until the server rolls out the
corresponding endpoints. See
[endpoint status](#current-api-endpoint-availability) for current availability.

### Utility commands

```bash
stare version          # print the installed stare version
stare auth login       # authenticate with CERN SSO
stare auth logout      # revoke tokens and delete local storage
stare auth status      # check whether a valid token is stored
stare auth info        # decode and display stored JWT claims
stare cache info       # show cache path, TTL, and size
stare cache clear      # delete all cached responses
```

`stare auth info` flags: `--access-token` (print raw PKCE access token),
`--id-token` (print raw id token), `--exchange` (show exchanged token claims).
Note: `--exchange` and `--id-token` are mutually exclusive.

## Library usage

```python
from stare import Glance

g = Glance()

# Search analyses (live)
result = g.analyses.search(query="referenceCode = ANA-HION-2018-01")
print(f"Found {result.total_rows} analyses")
for analysis in result.results:
    print(analysis.reference_code, analysis.short_title)

# Search papers (live)
paper_result = g.papers.search(query="status = Active")
for paper in paper_result.results:
    print(paper.reference_code, paper.status)

# Individual resource lookups (planned — return NotFoundError until live)
analysis = g.analyses.get("ANA-HION-2018-01")
paper = g.papers.get("HDBS-2018-33")
conf_note = g.conf_notes.get("ATLAS-CONF-2024-001")
pub_note = g.pub_notes.get("ATL-PHYS-PUB-2024-001")

# Publications search (planned)
pubs = g.publications.search(types=["Paper"], leading_groups=["HDBS"])

# Metadata (planned)
groups = g.groups.list()
subgroups = g.subgroups.list()
triggers = g.triggers.search(category="electron")
```

### Context manager

Use `Glance` as a context manager to explicitly control the underlying HTTP
connection lifecycle:

```python
with Glance() as g:
    result = g.analyses.search(query="status = Active")
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

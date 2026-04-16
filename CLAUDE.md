# stare — Contributor Guide

Python library and CLI for the CERN ATLAS Glance/Fence API.

## Architecture

```
User <--typer/CLI--> stare <--HTTPS (httpx)--> ATLAS Glance API
                       |
                       +--browser + local server--> CERN Keycloak (PKCE)
```

The library uses **httpx** for HTTP, **authlib** for OAuth2 PKCE, and
**pydantic** for all data models. The CLI is built with **typer** and **rich**.

## Project layout

```
src/stare/
├── __init__.py       # __version__, public re-exports (Glance)
├── py.typed          # PEP 561 marker
├── settings.py       # StareSettings via pydantic-settings (STARE_* env vars)
├── auth.py           # TokenManager: PKCE flow, token storage/refresh
├── client.py         # Glance client + resource accessors
├── cli.py            # typer CLI entry point
├── exceptions.py     # StareError hierarchy
└── models/
    ├── __init__.py    # re-exports all public models
    ├── common.py      # shared: Person, Groups, Meeting, Collision, Metadata, …
    ├── analysis.py    # Analysis, AnalysisPhase0
    ├── paper.py       # Paper, PaperPhase1, PaperPhase2, SubmissionPhase
    ├── conf_note.py   # ConfNote, ConfNotePhase1
    ├── pub_note.py    # PubNote, PubNotePhase1
    ├── search.py      # SearchResult, PaperSearchResult, PublicationRef, Trigger
    └── errors.py      # ApiErrorResponse
tests/
├── conftest.py                  # fixtures: mock_token_manager, mock_glance, etc.
├── fixtures/                    # JSON files with sample API responses
├── test_settings.py
├── test_exceptions.py
├── test_models.py
├── test_auth.py
├── test_client.py
├── test_cli.py
└── integration/
    └── test_live.py             # requires live CERN auth, run with --runslow
```

## Client usage pattern

```python
from stare import Glance

g = Glance()

# Currently live: GET /searchAnalysis
result = g.analyses.search(query='"referenceCode" = "ANA-HION-2018-01"')

# Currently live: GET /searchPaper
paper_result = g.papers.search(query='"referenceCode" = "HDBS-2018-33"')

# Planned endpoints (available once the API rolls them out)
analysis = g.analyses.get("ANA-HION-2018-01")
paper = g.papers.get("HDBS-2018-33")
groups = g.groups.list()
```

## Settings

All defaults are in `StareSettings`. Override via environment variables:

| Env var               | Default                                           |
| --------------------- | ------------------------------------------------- |
| `STARE_BASE_URL`      | `https://atlas-glance.cern.ch/atlas/analysis/api` |
| `STARE_AUTH_URL`      | `https://auth.cern.ch/…/openid-connect/auth`      |
| `STARE_TOKEN_URL`     | `https://auth.cern.ch/…/openid-connect/token`     |
| `STARE_CLIENT_ID`     | `stare`                                           |
| `STARE_SCOPES`        | `openid`                                          |
| `STARE_CALLBACK_PORT` | `8182`                                            |

## Auth flow (PKCE)

1. `stare login` spins up a local server on port 8182 (fixed, registered with
   CERN Keycloak), opens the browser
2. User authenticates with CERN SSO
3. Keycloak redirects to `http://localhost:8182/callback`
4. Tokens are stored as JSON in
   `platformdirs.user_data_dir("stare")/tokens.json`
5. Subsequent requests auto-refresh the access token using the refresh token

## Build and test commands

```bash
pixi run test          # quick tests (no live CERN needed)
pixi run test-slow     # all tests including live integration (requires stare login)
pixi run lint          # pre-commit + pylint
pixi run build         # build sdist + wheel
pixi run build-check   # verify the built distributions with twine
```

## Development setup

```bash
pixi install           # install all dependencies
pixi run pre-commit-install  # install git hooks
stare login            # authenticate with CERN SSO
```

## Model conventions

All pydantic models use:

- `model_config = ConfigDict(populate_by_name=True)` — allows both alias and
  Python-name access
- `Field(alias="camelCase")` — maps API JSON keys to Python snake_case names
- `None` defaults for all optional fields

## Adding a new endpoint

1. Add/update the pydantic model in `src/stare/models/`
2. Add a resource accessor method in `src/stare/client.py`
3. Add a CLI command in `src/stare/cli.py`
4. Write tests (TDD: test first, then implement)
5. Run `pixi run test` to verify

## Regenerating and translating the client scaffolding

When the OpenAPI spec at
`https://atlas-glance.cern.ch/atlas/analysis/api/docs/api.yml` is updated (new
endpoints, new fields, schema changes), regenerate the reference scaffolding and
then manually translate the relevant parts into `src/stare/`.

### Step 1 — Regenerate

`openapi-python-client` is not a pixi dependency (it's a one-off tool). Run it
with `uvx`:

```bash
uvx openapi-python-client generate \
    --url https://atlas-glance.cern.ch/atlas/analysis/api/docs/api.yml \
    --output-path _generated --overwrite
# Writes into _generated/ (gitignored — reference only, never shipped)
```

### Step 2 — What gets generated

`_generated/atlas_analysis_and_documents_api_client/` will contain:

- `models/` — `attrs`-based classes with `to_dict` / `from_dict`, one file per
  schema object (verbosely named e.g.
  `search_analysis_response_results_item_phase_0_approval_meeting_item.py`)
- `api/analysis/` — `sync` / `asyncio` / `sync_detailed` / `asyncio_detailed`
  functions for each endpoint
- `client.py` — `Client` / `AuthenticatedClient` (attrs-based, not pydantic)
- `types.py` — `Unset` sentinel, `Response` wrapper

### Step 3 — Translate into `src/stare/`

The generated code is a useful reference, not production code. Apply these
transformations:

| Generated pattern                                                            | stare pattern                                                              |
| ---------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| `attrs` `@_attrs_define` model                                               | `pydantic.BaseModel` subclass                                              |
| `Unset` sentinel for optional fields                                         | `None` default (`field: str \| None = None`)                               |
| Verbose names (`SearchAnalysisResponseResultsItemPhase0ApprovalMeetingItem`) | Short domain names (`Meeting`, `Phase0`, `Analysis`)                       |
| `Field(alias="camelCaseKey")` absent                                         | Add `Field(alias="camelCaseKey")` with `ConfigDict(populate_by_name=True)` |
| `from_dict` / `to_dict` class methods                                        | Replaced by pydantic `model_validate` / `model_dump`                       |
| `api/analysis/search_analysis.py` functions                                  | `AnalysisResource.search()` method in `client.py`                          |
| Error types omitted (cross-file `$ref`)                                      | Add manually from `models/errors.py` using the known schema                |

### Step 4 — What to look for on each regen

- **New endpoint files** under `_generated/.../api/` → add a new resource
  accessor method + resource class in `client.py`
- **New model files** under `_generated/.../models/` → add or extend pydantic
  models in the relevant `src/stare/models/*.py` file
- **Changed fields** (new keys, renamed keys, type changes) → update the
  corresponding pydantic model and its tests in `tests/test_models.py`
- **New error schemas** → update `models/errors.py`

### Step 5 — Test

After incorporating changes, run:

```bash
pixi run test
```

All model tests parse from the fixture JSON in `tests/fixtures/` — update those
fixtures to reflect any new/changed fields before running.

## SSL certificate bundle (`src/stare/data/CERN_chain.pem`)

The bundled `CERN_chain.pem` is passed as `verify=` to every `httpx.Client` that
talks to `atlas-glance.cern.ch`. It is needed because the server does not
include its intermediate CA in the TLS handshake (a server-side misconfiguration
that Python's SSL layer cannot work around on its own).

**Current bundle contents (as of 2026-04):**

- **Sectigo Public Server Authentication CA OV R36** (intermediate, ~2036
  expiry)
- **Sectigo Public Server Authentication Root R46** (root, ~2046 expiry)

`atlas-glance.cern.ch` switched from CERN Grid CA certificates to Sectigo
commercial certificates in early 2025. The Sectigo root is in standard OS trust
stores but the intermediate is not sent by the server, so we bundle it.

### Regenerating the bundle (maintainer task)

Run this when the server's certificate chain changes (check with
`openssl s_client -connect atlas-glance.cern.ch:443 -showcerts`).

```bash
# 1. Get the leaf cert AIA URL for the intermediate
echo | openssl s_client -connect atlas-glance.cern.ch:443 2>/dev/null \
  | openssl x509 -noout -text | grep "CA Issuers"

# 2. Download intermediate (DER) and convert to PEM
curl -s -o intermediate.crt <AIA-URL-from-above>
openssl x509 -in intermediate.crt -inform der -outform pem > intermediate.pem

# 3. Get root URL from intermediate cert, download (p7c), extract PEM
echo | openssl x509 -in intermediate.crt -inform der -noout -text | grep "CA Issuers"
curl -s -o root.p7c <root-AIA-URL>
openssl pkcs7 -in root.p7c -inform der -print_certs \
  | awk '/BEGIN CERT/{f=1;c++} f&&c==1{print} /END CERT/&&c==1{f=0}' > root.pem

# 4. Build bundle (intermediate first, root second)
cat intermediate.pem root.pem > src/stare/data/CERN_chain.pem

# 5. Verify — should print "OK"
echo | openssl s_client -connect atlas-glance.cern.ch:443 2>/dev/null \
  | openssl x509 > /tmp/leaf.pem
openssl verify -CAfile src/stare/data/CERN_chain.pem /tmp/leaf.pem
```

Commit `src/stare/data/CERN_chain.pem` — it is tracked in git because it is
bundled with the wheel and loaded at runtime via
`importlib.resources.as_file()`.

## API endpoints

| Endpoint                    | Status  | Resource accessor         |
| --------------------------- | ------- | ------------------------- |
| `GET /searchAnalysis`       | Live    | `g.analyses.search()`     |
| `GET /searchPaper`          | Live    | `g.papers.search()`       |
| `GET /analyses/{ref_code}`  | Planned | `g.analyses.get()`        |
| `GET /papers/{ref_code}`    | Planned | `g.papers.get()`          |
| `GET /confnotes/{ref_code}` | Planned | `g.conf_notes.get()`      |
| `GET /pubnotes/{ref_code}`  | Planned | `g.pub_notes.get()`       |
| `GET /publications/search`  | Planned | `g.publications.search()` |
| `GET /groups`               | Planned | `g.groups.list()`         |
| `GET /subgroups`            | Planned | `g.subgroups.list()`      |
| `GET /triggers/search`      | Planned | `g.triggers.search()`     |

## CLI structure

Analysis and paper commands are sub-apps with `search` and `get` subcommands:

```bash
stare analysis search [--query/-q] [--limit] [--offset] [--sort-by] [--sort-desc] [--json]
stare analysis get REF_CODE [--json]
stare paper search [--query/-q] [--limit] [--offset] [--sort-by] [--sort-desc] [--json]
stare paper get REF_CODE [--json]
```

CONF notes and PUB notes have only `get` (no search endpoint exists yet) and
remain flat top-level commands:

```bash
stare conf-note TEMP_REF_CODE [--json]
stare pub-note TEMP_REF_CODE [--json]
```

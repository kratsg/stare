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
    ├── search.py      # SearchResult, PublicationRef, Trigger
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

# Currently live (GET /searchAnalysis)
result = g.analyses.search(query='"referenceCode" = "ANA-HION-2018-01"')

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

The bundled `CERN_chain.pem` is used as the `verify=` argument for every
`httpx.Client` that talks to `atlas-glance.cern.ch`. It contains two PEM
certificates concatenated: the **CERN Grid CA** (intermediate) and the **CERN
Root Certification Authority 2** (root). Both are needed because
atlas-glance.cern.ch presents a certificate signed by the Grid CA, which is not
in most OS trust stores.

### Regenerating the bundle (maintainer task)

1. Download from [CERN CA Files](https://cafiles.cern.ch/cafiles/):
   - **CERN Root Certification Authority 2** — download as DER (`.crt`)
   - **CERN Grid Certification Authority** — download as PEM (`.pem`)

2. Convert the Root CA DER to PEM:

   ```bash
   openssl x509 -in CERN_ROOT_CA_2.crt -inform der -outform pem -out CERN_ROOT_CA_2.pem
   ```

3. Concatenate (Grid CA first, Root CA second):

   ```bash
   cat CERN_GRID_CA.pem CERN_ROOT_CA_2.pem > src/stare/data/CERN_chain.pem
   ```

4. Verify the bundle:

   ```bash
   openssl verify -CAfile src/stare/data/CERN_chain.pem src/stare/data/CERN_chain.pem
   ```

5. Commit `src/stare/data/CERN_chain.pem`. The file is tracked in git because it
   is bundled with the wheel and loaded at runtime via `importlib.resources`.

## API endpoints

| Endpoint                    | Status  | Resource accessor         |
| --------------------------- | ------- | ------------------------- |
| `GET /searchAnalysis`       | Live    | `g.analyses.search()`     |
| `GET /analyses/{ref_code}`  | Planned | `g.analyses.get()`        |
| `GET /papers/{ref_code}`    | Planned | `g.papers.get()`          |
| `GET /confnotes/{ref_code}` | Planned | `g.conf_notes.get()`      |
| `GET /pubnotes/{ref_code}`  | Planned | `g.pub_notes.get()`       |
| `GET /publications/search`  | Planned | `g.publications.search()` |
| `GET /groups`               | Planned | `g.groups.list()`         |
| `GET /subgroups`            | Planned | `g.subgroups.list()`      |
| `GET /triggers/search`      | Planned | `g.triggers.search()`     |

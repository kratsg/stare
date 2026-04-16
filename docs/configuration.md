---
icon: lucide/settings
---

# Configuration

## Environment variables

All settings come from `StareSettings`, which reads environment variables with
the `STARE_` prefix. Override any default by setting the corresponding variable
before running `stare` or importing the library.

| Variable          | Default                                                               | Description                     |
| ----------------- | --------------------------------------------------------------------- | ------------------------------- |
| `STARE_BASE_URL`  | `https://atlas-glance.cern.ch/atlas/analysis/api`                     | Glance/Fence API base URL       |
| `STARE_AUTH_URL`  | `https://auth.cern.ch/auth/realms/cern/protocol/openid-connect/auth`  | Keycloak authorization endpoint |
| `STARE_TOKEN_URL` | `https://auth.cern.ch/auth/realms/cern/protocol/openid-connect/token` | Keycloak token endpoint         |
| `STARE_CLIENT_ID` | `stare`                                                               | OAuth2 client identifier        |
| `STARE_SCOPES`    | `openid`                                                              | Space-separated OAuth2 scopes   |

## Using a custom settings object

Pass a custom `StareSettings` instance to `Glance` to override settings
programmatically — useful for testing or pointing at a staging server:

```python
from stare import Glance
from stare.settings import StareSettings

settings = StareSettings(
    base_url="https://staging.atlas-glance.cern.ch/atlas/analysis/api",
    client_id="stare-dev",
)
g = Glance(settings=settings)
```

## Token storage

Tokens are stored as JSON in the platform user data directory:

| Platform | Path                                              |
| -------- | ------------------------------------------------- |
| Linux    | `~/.local/share/stare/tokens.json`                |
| macOS    | `~/Library/Application Support/stare/tokens.json` |
| Windows  | `%APPDATA%\stare\tokens.json`                     |

The file contains the access token, refresh token, and expiry timestamp. It is
read and written by `TokenManager` and is never sent to any server other than
the CERN Keycloak token endpoint.

## Providing a token directly

If you already have a valid access token (e.g. from a CI secret or a separate
auth flow), pass it directly:

```python
g = Glance(token="eyJ...")
```

When `token` is provided, `TokenManager` is not used and no token file is read
or written.

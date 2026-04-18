---
icon: lucide/settings
---

# Configuration

## Environment variables

All settings come from [StareSettings][stare.settings.StareSettings], which
reads environment variables with the `STARE_` prefix. Override any default by
setting the corresponding variable before running `stare` or importing the
library.

| Variable                              | Default                                                                | Description                                                           |
| ------------------------------------- | ---------------------------------------------------------------------- | --------------------------------------------------------------------- |
| `STARE_BASE_URL`                      | `https://atlas-glance.cern.ch/atlas/analysis/api`                      | Glance/Fence API base URL                                             |
| `STARE_AUTH_URL`                      | `https://auth.cern.ch/auth/realms/cern/protocol/openid-connect/auth`   | Keycloak authorization endpoint                                       |
| `STARE_TOKEN_URL`                     | `https://auth.cern.ch/auth/realms/cern/protocol/openid-connect/token`  | Keycloak token endpoint                                               |
| `STARE_REVOCATION_URL`                | `https://auth.cern.ch/auth/realms/cern/protocol/openid-connect/revoke` | Keycloak token revocation endpoint                                    |
| `STARE_ISSUER`                        | `https://auth.cern.ch/auth/realms/cern`                                | Expected JWT issuer (validated on login)                              |
| `STARE_JWKS_URL`                      | `https://auth.cern.ch/auth/realms/cern/protocol/openid-connect/certs`  | JWKS endpoint for ID token signature verification                     |
| `STARE_CLIENT_ID`                     | `stare`                                                                | OAuth2 client identifier                                              |
| `STARE_SCOPES`                        | `openid`                                                               | Space-separated OAuth2 scopes                                         |
| `STARE_CALLBACK_PORT`                 | `8182`                                                                 | Local port for the PKCE redirect callback; must match Keycloak config |
| `STARE_VERBOSE`                       | `false`                                                                | Set to `1` to enable DEBUG-level request logging (httpx/httpcore)     |
| `STARE_EXCHANGE_AUDIENCE`             | _(not set)_                                                            | RFC 8693 target audience; enables token exchange when set             |
| `STARE_EXCHANGE_TOKEN_BUFFER_SECONDS` | `120`                                                                  | Re-exchange the token this many seconds before expiry                 |
| `STARE_TOKEN_EXPIRY_MARGIN_SECONDS`   | `60`                                                                   | Trigger refresh this many seconds before the access token expires     |
| `STARE_CA_BUNDLE`                     | `Sectigo`                                                              | TLS CA bundle: `Sectigo` (production) or `CERN` (staging)             |
| `STARE_WEB_BASE_URL`                  | `https://atlas-glance.cern.ch/atlas/analysis`                          | Web UI base URL for clickable hyperlinks in CLI output                |
| `STARE_CACHE_ENABLED`                 | `true`                                                                 | Enable on-disk HTTP response cache                                    |
| `STARE_CACHE_TTL_SECONDS`             | `28800`                                                                | Cache TTL in seconds (default: 8 hours)                               |
| `STARE_CACHE_DIR`                     | _(platform user cache dir)_                                            | Override the cache directory path                                     |

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

Tokens are stored in your OS native credential store by default (macOS Keychain,
Linux Secret Service, Windows Credential Locker), falling back to a JSON file in
the platform user data directory on headless systems. See
[Authentication — Token storage](auth.md#token-storage) for details.

## Providing a token directly

If you already have a valid access token (e.g. from a CI secret or a separate
auth flow), pass it directly:

```python
g = Glance(token="eyJ...")
```

When `token` is provided, `TokenManager` is not used and no token file is read
or written.

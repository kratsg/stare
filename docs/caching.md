---
icon: lucide/database
---

# HTTP response caching

`stare` caches every `GET` response on disk so repeated reads of the same
analysis or search query are instant after the first hit. The cache is powered
by [hishel](https://hishel.com) (RFC 9111 HTTP cache transport) and stored as
SQLite in a platform-appropriate user cache directory.

## Defaults

| Setting   | Default                                |
| --------- | -------------------------------------- |
| Enabled   | `true`                                 |
| TTL       | 8 hours (28,800 seconds)               |
| Backend   | SQLite                                 |
| Directory | `platformdirs.user_cache_dir("stare")` |

## Configuring

Set environment variables before running `stare`:

```bash
# Disable caching entirely
export STARE_CACHE_ENABLED=false

# Shorten the TTL to 1 hour
export STARE_CACHE_TTL_SECONDS=3600

# Use a custom directory
export STARE_CACHE_DIR=/tmp/stare-cache
```

Or programmatically:

```python
from stare import Glance
from stare.settings import StareSettings

g = Glance(settings=StareSettings(cache_enabled=False))
```

## Per-invocation bypass

Every CLI command accepts `--no-cache` to bypass the cache for that run:

```bash
stare analysis search -q 'referenceCode contain HION' --no-cache
```

## Cache management

Inspect and clear the on-disk cache:

```bash
# Show cache path, TTL, and current database size
stare cache info

# Delete every cached response (prompts for confirmation when stdin is a TTY)
stare cache clear

# Non-interactive clear (CI pipelines, scripts)
stare cache clear --yes
```

The cache lives in `cache-v2.db` inside the cache directory. `stare cache clear`
also removes a `cache.db` written by hishel 1.x, which hishel 2.x never reads.

## Security

The cache directory lives under the per-user platform cache path
(`platformdirs.user_cache_dir("stare")`), so cached responses are not shared
across user accounts. Within one account, the cache key includes the identity
the request is made as, so switching CERN users (or passing a different `token=`
to `Glance`) never serves another identity's cached response. A token that is a
JWT is identified by its issuer and subject, so a refreshed token for the same
user still hits the cache. Any other token is identified by its SHA-256 hash.

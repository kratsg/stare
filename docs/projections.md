---
icon: lucide/table-2
---

# Field projections

The `--projection` / `-p` flag on `stare analysis search` and
`stare paper search` lets you choose which fields appear as table columns,
without hardcoding anything on the server side.

## Syntax

```
-p "path1,path2,path3"
```

Multiple paths are comma-separated in a single string.

### Dot access

Walk nested model attributes with `.`:

```bash
stare analysis search -p "reference_code,groups.leading_group"
```

### List indexing

Use `[n]` to select a specific list element. Omitting the index implicitly
selects element `[0]`:

```bash
# Explicit index
stare analysis search -p "documentation.repositories[0].url"

# Implicit [0] — equivalent to the above
stare analysis search -p "documentation.repositories.url"
```

### Column aliases

Rename a column header with `:alias`:

```bash
stare analysis search -p "reference_code,groups.leading_group:group,status:st"
```

Output:

```
┏━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━━┓
┃ reference_code       ┃ group┃ st     ┃
┡━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━━┩
│ ANA-HION-2018-01     │ HI   │ Active │
```

### Missing paths

A path that does not exist on a given record produces an empty cell — no error
is raised.

## Examples

Show reference code, leading group, and first repository URL for all active
analyses:

```bash
stare analysis search \
  -q '"status" = "Active"' \
  -p "reference_code,groups.leading_group:group,documentation.repositories[0].url:repo"
```

Show paper reference code and phase1 state:

```bash
stare paper search -p "reference_code,phase1.state"
```

Combine with `--json` to get the raw API payload instead (projection is ignored
with `--json`):

```bash
stare analysis search --json | jq '.results[].referenceCode'
```

## Python API

The projection helpers are also available as a library:

```python
from stare.projection import parse_specs, resolve
from stare.models import Analysis

specs = parse_specs("reference_code,groups.leading_group:group")
analysis = Analysis.model_validate(...)

for spec in specs:
    value = resolve(analysis, spec.path)
    print(f"{spec.header}: {value}")
```

---
icon: lucide/search
---

# Query DSL

The `--query` / `-q` flag on `stare` **search commands** accepts a simple filter
expression validated and normalized client-side before being sent to the server.
Each search command validates against the field catalogue for its own record
type. See the
[endpoint status table](getting-started.md#current-api-endpoint-availability)
for which commands currently accept `--query`.

## Grammar

```lark
--8<-- "src/stare/data/query-grammar.lark"
```

`and` / `or` are case-insensitive at parse time; canonical output is uppercase
(`AND`, `OR`).

## Operators

| Operator      | Meaning                                                  |
| ------------- | -------------------------------------------------------- |
| `=`           | Exact match                                              |
| `!=`          | Not equal                                                |
| `contain`     | Field contains the value (array membership or substring) |
| `not-contain` | Field does not contain the value                         |

## Field names

Fields accept either `camelCase` or `snake_case` — both are normalized to
`camelCase` before being sent to the server:

```bash
# These are equivalent:
stare analysis search -q 'referenceCode = ANA-HION-2018-01'
stare analysis search -q 'reference_code = ANA-HION-2018-01'
```

Nested fields use a dot separator: `metadata.keywords`, `phase0.state`.

!!! note "Field catalogue is generated"

    Run `pixi run extract-fields` after an API update to regenerate both `src/stare/dsl/data/fields.toml` and the tables below.

## Quoting

Both the field name and the value may optionally be wrapped in **double
quotes**. Quotes are required on the value when it contains whitespace or
parentheses; for everything else they are optional.

The grammar's string token (`STRING: /"[^"]*"/`) does not permit embedded
double-quote characters, so values containing `"` are not supported even when
wrapped in double quotes. If your value contains a literal `"`, use `contain`
with a substring that avoids it, or reach out — escaped-quote support is not yet
implemented.

```bash
# These are equivalent:
stare analysis search -q 'referenceCode = HION'
stare analysis search -q '"referenceCode" = HION'
stare analysis search -q 'referenceCode = "HION"'

# Multi-word values require quotes:
stare analysis search -q 'shortTitle = "Phase Closed"'
stare paper search -q '"phase2.state" = "Phase Closed"'
```

Canonical output (`to_dsl()`) emits quotes on the value only when they are
required; bare single-token values are always emitted unquoted. Fields are
always emitted bare after normalization.

Only `"` (double quotes) are accepted — single quotes are not special.

## Values

Values are bare tokens or double-quoted strings. A bare value like
`ANA-HION-2018-01` or `Active` works without quotes. Wrap the value in double
quotes when it contains spaces:

```bash
stare analysis search -q 'shortTitle = "Phase Closed"'
stare analysis search -q 'metadata.keywords contain jets'
```

## Combining conditions

```bash
# AND (both must match)
stare analysis search -q 'status = Active and groups.leadingGroup = HDBS'

# OR (either may match)
stare analysis search -q 'status = Active or status = Approved'
```

`AND` binds tighter than `OR`: `a = 1 AND b = 2 OR c = 3` is parsed as
`(a = 1 AND b = 2) OR c = 3`.

!!! note "Parentheses are not supported by the server"

    The grammar accepts parentheses, but the Glance API ignores them. `stare` will log a warning and send the query without parentheses. Rely on `AND` binding tighter than `OR` instead of explicit grouping.

## Sorting

`--sort-by` and `--sort-desc` are independent of the query string and work with
any search command:

```bash
stare analysis search -q 'status = Active' --sort-by creationDate --sort-desc
stare paper search --sort-by referenceCode
```

## Skipping validation

Use `--no-validate` to bypass client-side field checking and send the raw string
directly to the server. This is useful for experimental server fields or when
you know the DSL is already in canonical form:

```bash
stare analysis search -q 'someNewField = value' --no-validate
```

## Analysis fields

--8<-- "snippets/fields-analysis.md"

## Paper fields

--8<-- "snippets/fields-paper.md"

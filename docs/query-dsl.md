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
--8<-- "src/stare/dsl/grammar.lark"
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

!!! note "Field catalogue mirrors `fields.toml`" The field tables below are
extracted from the server's OpenAPI spec by `pixi run extract-fields`, which
writes `src/stare/dsl/data/fields.toml`. Re-run after an API update and manually
update the tables below to match.

## Values

Values are bare tokens (no quotes, no spaces). A value like `ANA-HION-2018-01`
or `Active` works; a multi-word title does not — use `contain` instead:

```bash
# Can't express a multi-word value directly — use contain:
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

!!! note "Parentheses are not supported by the server" The grammar accepts
parentheses, but the Glance API ignores them. `stare` will log a warning and
send the query without parentheses. Rely on `AND` binding tighter than `OR`
instead of explicit grouping.

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

| Group      | Fields                                                                                                                                                                                   |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Top-level  | `creationDate`, `publicShortTitle`, `referenceCode`, `shortTitle`, `status`                                                                                                              |
| `groups`   | `groups.leadingGroup`, `groups.otherGroups`, `groups.subgroups`                                                                                                                          |
| `metadata` | `metadata.keywords`, `metadata.mvaMlTools`, `metadata.triggers`                                                                                                                          |
| `phase0`   | `phase0.datasetUsed`, `phase0.editorialBoardFormedOn`, `phase0.mainPhysicsAim`, `phase0.methods`, `phase0.modelTested`, `phase0.pgcOrSgcSignOffDate`, `phase0.startDate`, `phase0.state` |

## Paper fields

| Group             | Fields                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| ----------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Top-level         | `fullTitle`, `publicShortTitle`, `referenceCode`, `rivetRoutinesUrl`, `shortTitle`, `status`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `groups`          | `groups.leadingGroup`, `groups.otherGroups`, `groups.subgroups`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `metadata`        | `metadata.keywords`, `metadata.mvaMlTools`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `phase1`          | `phase1.atlasMeetingDate`, `phase1.draftReleasedDate`, `phase1.editorialBoardDraftSignOffDate`, `phase1.editorialBoardFormedOn`, `phase1.languageEditorsSignOffDate`, `phase1.pgcApprovalDate`, `phase1.presentationDate`, `phase1.pubcommChairOrDeputyOrDelegated.cernCcid`, `phase1.pubcommChairOrDeputyOrDelegated.firstName`, `phase1.pubcommChairOrDeputyOrDelegated.lastName`, `phase1.pubcommSignOffDate`, `phase1.spokespersonOrDeputyOrDelegated.cernCcid`, `phase1.spokespersonOrDeputyOrDelegated.firstName`, `phase1.spokespersonOrDeputyOrDelegated.lastName`, `phase1.startDate`, `phase1.state` |
| `phase2`          | `phase2.draft2CernSignOffDate`, `phase2.draft2ReleasedDate`, `phase2.draft2SentToCernDate`, `phase2.editorialBoardDraft2SignOffDate`, `phase2.editorialBoardRevisedSignOffDate`, `phase2.paperClosureDate`, `phase2.preliminaryPlotsAndResultsReleased`, `phase2.pubcommChairOrDeputyOrDelegated.cernCcid`, `phase2.pubcommChairOrDeputyOrDelegated.firstName`, `phase2.pubcommChairOrDeputyOrDelegated.lastName`, `phase2.pubcommChairOrDeputyOrDelegatedSignOffDate`, `phase2.spokespersonOrDeputyOrDelegatedSignOffDate`, `phase2.startDate`, `phase2.state`                                                |
| `relatedAnalysis` | `relatedAnalysis.referenceCode`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `submission`      | `submission.arXivSubmissionDate`, `submission.dateOf1stProof`, `submission.dateOf1stRefereeReport`, `submission.finalSubmissionJournal`, `submission.finalTitleTex`, `submission.journalAcceptanceDate`, `submission.publishedOnlineOn`, `submission.startDate`, `submission.state`                                                                                                                                                                                                                                                                                                                            |

!!! note "status field" `status` is included in both catalogues. If the server
rejects it as a filter field, re-generate without it or use `--no-validate` as a
workaround.

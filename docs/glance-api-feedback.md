# Feedback on the ATLAS Glance/Fence API design

This document collects concrete issues and suggestions for the Glance team
based on the experience of writing `stare` — a Python client and CLI for the
analysis/documents API.  The goal is to make the API easier to consume from
any language, not just Python.

---

## 1. Inconsistent "total count" field

`GET /searchAnalysis` returns:

```json
{ "totalRows": 1, "results": [...] }
```

`GET /searchPaper` returns:

```json
{ "numberOfResults": "1", "results": [...] }
```

Two problems:
- Different field names (`totalRows` vs `numberOfResults`) for the same concept.
- Different types: `totalRows` is an integer, `numberOfResults` is a **string**.

**Suggestion:** Use the same field name and type across all search endpoints.
`totalRows: integer` (or `total: integer`) is cleaner for client-side
pagination math.

---

## 2. Inconsistent `leadingGroup` type

In `SearchAnalysisResponse`, `groups.leadingGroup` is:

```yaml
leadingGroup:
  type: array
  items:
    type: string
```

In `SearchPaperResponse`, `groups.leadingGroup` is:

```yaml
leadingGroup:
  type: string
```

A field with the same name and purpose should have the same type everywhere.
If an analysis can have multiple leading groups, papers probably can too.  If
only one is ever returned for a paper, use a single-element array (not a bare
string) so client code doesn't need a conditional.

---

## 3. `isContactEditor` modelled as string instead of boolean

Both `SearchAnalysisResponse` and `SearchPaperResponse` define:

```yaml
analysisTeam:
  items:
    properties:
      isContactEditor:
        type: string
```

If this is a yes/no flag it should be `type: boolean` so clients don't have
to guess whether `"true"`, `"1"`, `"yes"`, or `"True"` is what comes back.

---

## 4. DSL query language (`queryString`) is under-documented

The `queryString` parameter is described as:

> Supports operators such as `contain`, `not-contain`, `=`, and `!=` over
> the available searchable properties (e.g. `creationDate`, `referenceCode`,
> `keywords`).

For a client library to expose this usefully, we need:

- A complete list of searchable field names per resource.
- Whether field names are case-sensitive.
- How to combine multiple conditions (is `AND` / `OR` supported? parentheses?).
- Escaping rules for values that contain spaces or special characters.
- Whether the same DSL works identically for `/searchAnalysis` and
  `/searchPaper` (the field sets are different, so presumably the searchable
  keys differ too).

**Suggestion:** Add a `/searchAnalysis/schema` (or similar) endpoint that
returns the list of filterable fields and their types, and/or expand the
OpenAPI description with a full grammar example.

---

## 5. No `/searchConfNote` or `/searchPubNote`

There are search endpoints for analyses and papers but not for CONF notes or
PUB notes.  Users who want to list "all CONF notes from HDBS in 2024" have
no direct path; they must use `/publications/search` (which returns minimal
data) and then fetch each record individually.

**Suggestion:** Add `GET /searchConfNote` and `GET /searchPubNote` with the
same DSL filter support as the existing search endpoints.

---

## 6. No direct `GET /{resource}/{id}` in the OpenAPI spec

The OpenAPI spec (`api.yml`) only documents `/searchAnalysis` and
`/searchPaper`.  The individual-record endpoints (`/analyses/{ref_code}`,
`/papers/{ref_code}`, `/confnotes/{temp_ref_code}`, `/pubnotes/{temp_ref_code}`)
are implemented in `stare` based on the Confluence spec but are not in
`api.yml`.

**Suggestion:** Add all individual-record GET endpoints to the OpenAPI spec
so they are discoverable via `/docs/api.yml`.

---

## 7. Metadata field naming: `collisions` vs `collision`

In analysis metadata:

```yaml
metadata:
  collisions:   # plural
    type: array
```

In paper metadata:

```yaml
metadata:
  collision:    # singular
    type: array
```

Same concept, different key names.  Pick one (prefer plural for an array).

---

## 8. `relatedAnalysis` vs `relatedPublications` shape mismatch

Analysis has:

```yaml
relatedPublications:
  type: array
  items:
    properties:
      type: string
      referenceCode: string
```

Paper has:

```yaml
relatedAnalysis:
  type: object
  properties:
    referenceCode: string
```

If a paper can only be related to one analysis, the object form is fine — but
it would be cleaner to use an array even for single items, so client code is
uniform.  The field name asymmetry (`relatedPublications` vs `relatedAnalysis`)
is also confusing.

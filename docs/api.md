---
icon: lucide/code-2
---

# API reference

## Client

::: stare.Glance

## Resource accessors

::: stare.client.AnalysisResource

::: stare.client.PaperResource

::: stare.client.ConfNoteResource

::: stare.client.PubNoteResource

::: stare.client.PublicationResource

::: stare.client.GroupResource

::: stare.client.SubgroupResource

::: stare.client.TriggerResource

## Authentication

::: stare.auth.TokenManager

::: stare.storage.TokenStorage

::: stare.storage.FileTokenStorage

::: stare.storage.KeyringTokenStorage

## Settings

::: stare.settings.StareSettings

## Exceptions

::: stare.exceptions.StareError

::: stare.exceptions.AuthenticationError

::: stare.exceptions.TokenExpiredError

::: stare.exceptions.ApiError

::: stare.exceptions.NotFoundError

::: stare.exceptions.ForbiddenError

::: stare.exceptions.UnauthorizedError

::: stare.exceptions.ResponseParseError

## DSL

The query DSL is available for programmatic use. See [Query DSL](query-dsl.md)
for the syntax reference.

::: stare.dsl.parse_dsl

::: stare.dsl.Condition

::: stare.dsl.And

::: stare.dsl.Or

::: stare.dsl.models.Operator

::: stare.dsl.FieldRegistry

::: stare.dsl.DSLError

::: stare.dsl.DSLSyntaxError

::: stare.dsl.DSLValidationError

## Enums

All enums are also available in a *lenient* form via the `Lenient*` type aliases
(e.g. `LenientAnalysisStatus`). Lenient aliases accept unknown strings gracefully
— logging a warning and storing the raw value rather than raising a validation error.

::: stare.models.enums.AnalysisStatus

::: stare.models.enums.PaperStatus

::: stare.models.enums.PhaseState

::: stare.models.enums.CollisionType

::: stare.models.enums.RepositoryType

::: stare.models.enums.PublicationType

::: stare.models.enums.MeetingType

## URLs

URL builders for the ATLAS Glance web UI. Used internally to generate
clickable hyperlinks in CLI output; also available for library callers.

::: stare.urls.analysis_url

::: stare.urls.paper_url

::: stare.urls.conf_note_url

::: stare.urls.pub_note_url

## Models

### Shared

::: stare.models.Link

::: stare.models.Meeting

### Analysis

::: stare.models.Analysis

::: stare.models.AnalysisSearchResult

### Papers and notes

::: stare.models.Paper

::: stare.models.PaperSearchResult

::: stare.models.ConfNote

::: stare.models.PubNote

### Publications and triggers

::: stare.models.PublicationRef

::: stare.models.Trigger

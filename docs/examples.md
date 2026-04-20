---
icon: lucide/book-open
---

# Examples

All library examples use the [`Glance`][stare.Glance] client. Authentication is
handled automatically from your stored token (run `stare auth login` once). See
[Authentication](auth.md) for CI environments that need token injection.

---

## Search analyses

=== "Python"

    ```python
    from stare import Glance

    g = Glance()
    result = g.analyses.search()  # (1)!
    print(f"{result.number_of_results} analyses total")
    for analysis in result.results:
        print(analysis.reference_code, analysis.short_title)
    ```

    1. No query means "return everything" — the server default is 50 results per
       page. Use `limit` and `offset` to paginate; see the
       [pagination example](#paginate-through-all-results) below.

=== "CLI"

    ```bash
    stare analysis search
    stare analysis search --json  # (1)!
    ```

    1. `--json` forces machine-readable JSON output in a terminal. JSON is
       emitted automatically when stdout is a pipe or file.

---

## Filter with the DSL

=== "Python"

    ```python
    from stare import Glance

    g = Glance()
    result = g.analyses.search(
        query="groups.leadingGroup = HIGG",  # (1)!
        limit=10,
        sort_by="creationDate",  # (2)!
        sort_desc=True,
    )
    for analysis in result.results:
        print(analysis.reference_code, analysis.status)
    ```

    1. The query language supports `=`, `!=`, `contain`, and `not-contain`. Fields
       use camelCase API names. See [Query DSL](query-dsl.md) for the full grammar
       and field catalogue.
    2. `sort_by` accepts any camelCase API field name. Pair with `sort_desc=True`
       to reverse the order.

=== "CLI"

    ```bash
    # Filter by leading group
    stare analysis search -q 'groups.leadingGroup = HIGG' -n 10

    # Sort by creation date, most recent first
    stare analysis search -q 'groups.leadingGroup = HIGG' \
      --sort-by creationDate --sort-desc --limit 10

    # Pipe to jq for field extraction
    stare analysis search -q 'groups.leadingGroup = HIGG' \
      | jq -r '.results[] | select(.status == "Active") | .referenceCode'
    ```

---

## Look up a specific analysis

=== "Python"

    ```python
    from stare import Glance

    g = Glance()
    result = g.analyses.search(
        query="referenceCode = ANA-HION-2018-01",
        limit=1,
    )
    analysis = result.results[0]
    print(analysis.reference_code, analysis.status)
    if analysis.groups:
        print("leading group:", analysis.groups.leading_group)
    ```

=== "CLI"

    ```bash
    stare analysis search -q 'referenceCode = ANA-HION-2018-01'

    # JSON output — pipe to jq for field extraction
    stare analysis search -q 'referenceCode = ANA-HION-2018-01' --json \
      | jq '.results[0] | {referenceCode, status}'
    ```

---

## Inspect the analysis team

```python
from stare import Glance

g = Glance()
result = g.analyses.search(query="referenceCode = ANA-HION-2018-01", limit=1)
analysis = result.results[0]

editors = [m for m in analysis.analysis_team if m.is_contact_editor]  # (1)!
print(f"{len(editors)} contact editor(s):")
for editor in editors:
    print(f"  {editor.first_name} {editor.last_name} ({editor.cern_ccid})")
```

1. `is_contact_editor` is a `bool`. Contact editors are the primary points of
   contact for the analysis.

---

## Inspect phase 0 meetings

```python
from stare import Glance
from stare.models.enums import MeetingType

g = Glance()
result = g.analyses.search(query="referenceCode = ANA-HION-2018-01", limit=1)
analysis = result.results[0]

if analysis.phase0:
    for meeting in analysis.phase0.meetings:  # (1)!
        label = MeetingType(meeting.meeting_type).name.replace("_", " ").title()
        print(f"[{label}] {meeting.title} — {meeting.date}")
        if meeting.link and meeting.link.url:
            print(f"  {meeting.link.url}")
```

1. Meetings from all four phase 0 buckets (`eoiMeeting`,
   `editorialBoardRequestMeeting`, `preApprovalMeeting`, `approvalMeeting`) are
   flattened into a single `meetings` list, each tagged with its
   [`MeetingType`][stare.models.enums.MeetingType].

---

## Search papers

=== "Python"

    ```python
    from stare import Glance

    g = Glance()
    result = g.papers.search(
        query="groups.leadingGroup = HDBS",
        limit=10,
    )
    print(f"{result.number_of_results} papers total, showing {len(result.results)}")
    for paper in result.results:
        print(paper.reference_code, paper.status)
    ```

=== "CLI"

    ```bash
    stare paper search -q 'groups.leadingGroup = HDBS' -n 10

    # Emit (reference_code, status) pairs as TSV
    stare paper search -q 'groups.leadingGroup = HDBS' \
      | jq -r '.results[] | [.referenceCode, .status] | @tsv'
    ```

---

## Access paper submission data

=== "Python"

    ```python
    from stare import Glance

    g = Glance()
    result = g.papers.search(query="referenceCode = EXOT-2018-14", limit=1)
    paper = result.results[0]

    if paper.submission:  # (1)!
        for link in paper.submission.arxiv_urls:  # (2)!
            print(f"arXiv: {link.label}  →  {link.url}")
        for pub in paper.submission.final_journal_publications:  # (3)!
            print(f"Journal: {pub.label}  →  {pub.url}")
        for brief in paper.submission.physics_briefings:
            print(f"Briefing: {brief.label}  →  {brief.url}")
    ```

    1. `submission` is `None` when the paper has not yet reached the submission
       phase.
    2. A paper may have multiple arXiv entries (e.g. when the arXiv identifier
       changes during the submission process).
    3. Final journal publications and physics briefings are also lists — a paper can
       appear in more than one journal or have several briefings.

=== "CLI"

    ```bash
    stare paper search -q 'referenceCode = EXOT-2018-14' --json \
      | jq '.results[0].submission.arXivUrls'

    stare paper search -q 'referenceCode = EXOT-2018-14' --json \
      | jq -r '.results[0].submission.finalJournalPublication[] | "\(.label)  →  \(.url)"'
    ```

---

## Paginate through all results

=== "Python"

    ```python
    from stare import Glance

    g = Glance()
    limit = 50
    offset = 0
    all_codes: list[str] = []

    while True:
        result = g.analyses.search(
            query="groups.leadingGroup = HIGG",
            limit=limit,
            offset=offset,
        )
        all_codes.extend(a.reference_code for a in result.results if a.reference_code)
        offset += len(result.results)
        if offset >= (result.number_of_results or 0):  # (1)!
            break

    print(f"Collected {len(all_codes)} HIGG analyses")
    ```

    1. `number_of_results` is the server-side total count, not the number of items
       in the current page. Compare your running offset against it to know when
       you've exhausted all pages.

=== "CLI"

    ```bash
    # First page of 25
    stare analysis search -q 'groups.leadingGroup = HIGG' --limit 25

    # Second page of 25
    stare analysis search -q 'groups.leadingGroup = HIGG' --limit 25 --offset 25

    # Save a full result set to disk (auto-JSON when redirected)
    stare analysis search -q 'groups.leadingGroup = HIGG' > higg_analyses.json
    jq '.results | length' higg_analyses.json
    ```

---

## Disable the cache

=== "Python"

    ```python
    from stare import Glance
    from stare.settings import StareSettings

    g = Glance(settings=StareSettings(cache_enabled=False))  # (1)!
    result = g.analyses.search(limit=5)
    ```

    1. Disabling the cache forces a fresh HTTP request every time. This is useful in
       scripts that need up-to-the-minute data, or in tests that must not replay
       stale responses. See [Caching](caching.md) for TTL configuration and
       per-invocation bypass via `--no-cache`.

=== "CLI"

    ```bash
    # Skip cache for a single invocation
    stare analysis search --no-cache

    # All HDBS papers, fresh data
    stare paper search -q 'groups.leadingGroup = HDBS' --no-cache
    ```

---

## Use as a context manager

```python
from stare import Glance

with Glance() as g:  # (1)!
    analyses = g.analyses.search(limit=5)
    papers = g.papers.search(limit=5)

print(analyses.results[0].reference_code)
```

1. The context manager closes the underlying HTTP connection pool when the block
   exits. Outside a `with` block the connection pool is managed automatically,
   but the context manager form is preferred in long-running scripts.

---

## Handle errors

```python
from stare import Glance
from stare.exceptions import AuthenticationError, StareError

try:
    g = Glance()
    result = g.analyses.search(query="referenceCode = ANA-HION-2018-01")
except AuthenticationError:  # (1)!
    print("Not authenticated — run `stare auth login` first")
except StareError as exc:  # (2)!
    print(f"API error: {exc}")
```

1. [`AuthenticationError`][stare.exceptions.AuthenticationError] is raised when
   no valid token is stored or the stored token cannot be refreshed. Running
   `stare auth login` resolves this.
2. All `stare` exceptions inherit from
   [`StareError`][stare.exceptions.StareError] — catching it handles network
   failures, parse errors, and HTTP error responses in one place.

---

## Token injection (CI / scripting)

In environments where interactive browser login is not possible, pass a token
directly:

```python
import os
from stare import Glance

g = Glance(token=os.environ["GLANCE_TOKEN"])  # (1)!
result = g.analyses.search(limit=5)
```

1. The `token` keyword skips the OS credential store entirely. Obtain the token
   from `stare auth info --access-token` and store it as a CI secret.

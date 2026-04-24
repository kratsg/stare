"""Shared pydantic models reused across all Glance resource types."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Generic, TypeVar

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    ValidationError,
    model_validator,
)
from pydantic.alias_generators import to_camel
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from stare.exceptions import EnrichedErrorResponse, ResponseParseError
from stare.models.enums import (
    LenientCollisionType,
    LenientPublicationType,
    LenientRepositoryType,
    MeetingType,
)

if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import Any

    from typing_extensions import Self


def _format_loc(loc: tuple[str | int, ...]) -> str:
    """Format a pydantic loc tuple into a readable path string.

    Integer indices are rendered as ``[n]`` (e.g. ``results[207].extraMetadata``)
    rather than dot-joined numbers, matching standard JSON-path notation.
    """
    if not loc:
        return "(root)"
    result = ""
    for part in loc:
        if isinstance(part, int):
            result += f"[{part}]"
        else:
            result = f"{result}.{part}" if result else str(part)
    return result


def _extract_context(obj: Any, loc: tuple[str | int, ...]) -> str | None:
    """Walk to the parent of the failing field and return a referenceCode label."""
    try:
        node = obj
        for part in loc[:-1]:
            node = node[part]
            if isinstance(node, dict):
                ref = node.get("referenceCode")
                if ref:
                    return f"referenceCode={ref!r}"
    except (KeyError, IndexError, TypeError):
        pass
    return None


def _truncate_with_focus(
    obj: Any, loc: tuple[str | int, ...], max_list: int = 5
) -> Any:
    """Return a truncated version of obj focused on the failing location."""
    if not loc:
        return obj

    head, *tail = loc

    if isinstance(obj, list) and isinstance(head, int):
        idx = head
        n = len(obj)

        # Determine window around the failing index
        start = max(0, idx - max_list // 2)
        end = min(n, idx + max_list // 2 + 1)

        truncated = []

        if start > 0:
            truncated.append(f"... {start} items ...")

        for i in range(start, end):
            if i == idx:
                truncated.append(_truncate_with_focus(obj[i], tuple(tail), max_list))
            else:
                truncated.append("{...}")

        if end < n:
            truncated.append(f"... {n - end} more items ...")

        return truncated

    if isinstance(obj, dict) and isinstance(head, str):
        result = {}

        for k, v in obj.items():
            if k == head:
                result[k] = _truncate_with_focus(v, tuple(tail), max_list)
            else:
                result[k] = "{...}"

        return result

    return obj


def _format_parse_error(
    model_name: str, error: ValidationError, obj: Any = None
) -> tuple[str, list[EnrichedErrorResponse]]:
    """Build a human-readable summary of a pydantic ValidationError.

    For scalar inputs the offending value is shown inline; complex inputs
    (dicts/lists) are omitted from the line to keep the output concise — the
    caller may display the full raw payload separately.

    When *obj* (the raw API response) is provided, a ``referenceCode`` label is
    extracted from the parent of the failing field and appended for context.
    """
    errors = error.errors()
    count = len(errors)
    lines = [
        f"Failed to parse {model_name} from API response ({count} validation error(s)):"
    ]
    enriched_errors = []

    for i, err in enumerate(errors, 1):
        loc_tuple: tuple[str | int, ...] = err.get("loc", ())
        loc = _format_loc(loc_tuple)
        msg = err.get("msg", "unknown error")
        input_val = err.get("input")
        context = _extract_context(obj, loc_tuple) if obj is not None else None
        line = f"  {i}. {loc}: {msg}"
        if context:
            line += f" ({context})"
        if input_val is not None and not isinstance(input_val, dict | list):
            line += f" (got: {type(input_val).__name__} = {input_val!r})"
        lines.append(line)

        snippet = _truncate_with_focus(obj, loc_tuple) if obj is not None else None

        enriched_errors.append(
            EnrichedErrorResponse.model_validate(
                {
                    "loc": loc_tuple,
                    "loc_str": loc,
                    "message": msg,
                    "context": context,
                    "snippet": snippet,
                    "input_val": input_val,
                }
            )
        )

    return "\n".join(lines), enriched_errors


class _Base(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    @classmethod
    def model_validate(
        cls,
        obj: Any,
        *args: Any,
        verbose: bool = False,
        **kwargs: Any,
    ) -> Self:
        try:
            return super().model_validate(obj, *args, **kwargs)
        except ValidationError as exc:
            msg, details = _format_parse_error(cls.__name__, exc, obj=obj)

            raise ResponseParseError(
                msg,
                raw_data=obj if verbose else None,
                details=details,
            ) from exc


_T = TypeVar("_T")


class _ListRootModel(RootModel[list[_T]], Generic[_T]):
    """Generic base for RootModel wrappers over a list, forwarding list-like protocol."""

    root: list[_T] = Field(default_factory=list)

    def __iter__(self) -> Iterator[_T]:  # type: ignore[override]
        return iter(self.root)

    def __len__(self) -> int:
        return len(self.root)

    def __getitem__(self, index: int) -> _T:
        return self.root[index]

    def __bool__(self) -> bool:
        return bool(self.root)


class Link(_Base):
    """A labelled URL, optionally rendered as a Rich clickable hyperlink."""

    label: str | None = None
    url: str | None = None

    def __rich__(self) -> Text:
        """Render as a Rich clickable hyperlink when a URL is present."""
        display = self.label or self.url or ""
        if self.url:
            return Text(display, style=f"link {self.url}")
        return Text(display)


# Backward-compat aliases so existing imports keep working.
AmiGlanceLink = Link
InternalDocument = Link


class Person(_Base):
    """A CERN person (base for team members, contacts, board members)."""

    cern_ccid: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None


class TeamMember(Person):
    """A member of an analysis team."""

    is_contact_editor: bool | None = None


class EditorialBoardMember(Person):
    """A member of a publication editorial board."""

    is_chair: bool | None = None
    is_ex_officio: bool | None = None


class AnalysisContact(Person):
    """An analysis contact with a start/end assignment period."""

    start_date: date | None = None
    end_date: date | None = None


class EditorialBoard(_ListRootModel[EditorialBoardMember]):
    """Ordered list of editorial board members, rendered as a titled panel."""

    def __rich__(self) -> Panel:
        """Return a Rich Panel listing all editorial board members."""
        eb_table = Table(show_header=False, expand=True)
        eb_table.add_column()
        for eb in self:
            name = f"{eb.first_name} {eb.last_name}"
            if eb.is_chair:
                name = f"[bold]{name}[/bold]"
            elif eb.is_ex_officio:
                name = f"[dim]{name}[/dim]"
            eb_table.add_row(name)
        return Panel(eb_table, title="Editorial Board")


class AnalysisTeam(_ListRootModel[TeamMember]):
    """Ordered list of team members, rendered as a titled panel with contact-editor highlight."""

    def __rich__(self) -> Panel:
        """Return a Rich Panel listing all team members, contact editors first."""
        team_table = Table(show_header=True, header_style="bold magenta", expand=True)
        team_table.add_column("Name")
        team_table.add_column("CCID", justify="right")
        team_sorted = sorted(self, key=lambda p: not p.is_contact_editor)
        for p in team_sorted:
            name = f"{p.first_name} {p.last_name}"
            if p.is_contact_editor:
                name = f"[bold yellow]★ {name}[/bold yellow]"
            team_table.add_row(name, p.cern_ccid or "")
        return Panel(team_table, title=f"Team ({len(self)})")


class AnalysisContacts(_ListRootModel[AnalysisContact]):
    """Ordered list of analysis contacts, rendered as a titled panel with date ranges."""

    def __rich__(self) -> Panel:
        """Return a Rich Panel listing all analysis contacts with date ranges."""
        table = Table(show_header=True, header_style="bold magenta", expand=True)
        table.add_column("Name")
        table.add_column("Start", justify="right")
        table.add_column("End", justify="right")
        for c in self:
            table.add_row(
                f"{c.first_name} {c.last_name}",
                str(c.start_date) if c.start_date else "",
                str(c.end_date) if c.end_date else "",
            )
        return Panel(table, title="Contacts")


class Groups(_Base):
    """Leading group, subgroups, and other groups for a publication."""

    leading_group: str | None = None
    subgroups: list[str] = Field(default_factory=list)
    other_groups: list[str] = Field(default_factory=list)

    def __rich__(self) -> Panel:
        """Return a Rich Panel showing leading, sub-, and other groups."""
        group_table = Table.grid(padding=(0, 1))
        group_table.add_column(style="bold cyan", justify="right")
        group_table.add_column()
        if self.leading_group:
            group_table.add_row("Leading", f" {self.leading_group}")
        if self.subgroups:
            group_table.add_row("Subgroups", f" {', '.join(self.subgroups)}")
        if self.other_groups:
            group_table.add_row("Other", f" {', '.join(self.other_groups)}")
        return Panel(group_table, title="Groups", expand=True)


class Collision(_Base):
    """A collision dataset descriptor (centre-of-mass energy, luminosity, etc.)."""

    type: LenientCollisionType | None = None
    year: str | None = None
    run: str | None = None
    ecm_value: str | None = None
    ecm_unit: str | None = None
    luminosity_value: str | None = None
    luminosity_unit: str | None = None

    def __rich__(self) -> Panel:
        """Return a Rich Panel showing run, centre-of-mass energy, and luminosity."""
        physics = Table.grid(padding=(0, 1))
        physics.add_column(style="bold cyan", justify="right")
        physics.add_column()
        physics.add_row("Run", f"{self.run} ({self.year})")
        physics.add_row("√s", f"{self.ecm_value} TeV")
        physics.add_row("L", f"{self.luminosity_value} fb⁻¹")
        return Panel(physics, title="Physics", expand=True)


class Collisions(_ListRootModel[Collision]):
    """All collision datasets for a resource, rendered as a combined Physics panel."""

    def __rich__(self) -> Panel:
        """Return a Rich Panel combining all collision datasets into one Physics view."""
        physics = Table.grid(padding=(0, 1))
        physics.add_column(style="bold cyan", justify="right")
        physics.add_column()
        for i, coll in enumerate(self):
            if i > 0:
                physics.add_row("", "")
            physics.add_row("Run", f"{coll.run} ({coll.year})")
            physics.add_row("√s", f"{coll.ecm_value} TeV")
            physics.add_row("L", f"{coll.luminosity_value} fb⁻¹")
        return Panel(physics, title="Physics", expand=True)


class Metadata(_Base):
    """Physics and technical metadata shared across resource types.

    Not all fields are populated for every resource type; absent fields are None.
    """

    collisions: Collisions = Field(default_factory=Collisions)
    keywords: list[str] = Field(default_factory=list)
    statistical_tools: list[str] = Field(default_factory=list)
    mva_ml_tools: list[str] = Field(default_factory=list)
    triggers: list[str] = Field(default_factory=list)
    # Analysis-specific; None means no frameworks reported (distinct from empty dict)
    analysis_frameworks: dict[str, list[str]] | None = None
    # Paper-specific
    rivet_routines: list[str] = Field(default_factory=list)


class Repository(Link):
    """A code or documentation repository."""

    gitlab_id: str | None = None
    type: LenientRepositoryType | None = None


class Documentation(_Base):
    """Repositories and supporting documents for a publication."""

    repositories: list[Repository] = Field(default_factory=list)
    supporting_internal_documents: list[Link] = Field(default_factory=list)


class Meeting(_Base):
    """A recorded meeting (EOI, editorial board request, pre-approval, approval, etc.).

    The API sends a flat ``linkLabel`` / ``link`` pair; we fold them into a
    single nested ``Link`` object on ingestion.
    """

    title: str | None = None
    date: datetime | None = None
    comments: str | None = None
    link: Link | None = None

    @model_validator(mode="before")
    @classmethod
    def _fold_link_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        # API sends flat label/url fields; fold them into a nested Link object.
        if "link" not in data and ("label" in data or "url" in data):
            label = data.pop("label", None)
            url = data.pop("url", None)
            if label is not None or url is not None:
                data["link"] = {"label": label, "url": url}
        return data


class TypedMeeting(Meeting):
    """A Meeting tagged with its phase0 role (EOI, EB request, pre-approval, approval)."""

    meeting_type: MeetingType


class RelatedPublication(_Base):
    """A reference to a related publication (analysis, paper, CONF/PUB note)."""

    reference_code: str | None = None
    type: LenientPublicationType | None = None

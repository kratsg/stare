"""Shared pydantic models reused across all Glance resource types."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from pydantic.alias_generators import to_camel
from rich.text import Text

from stare.exceptions import ResponseParseError
from stare.models.enums import (
    LenientCollisionType,
    LenientPublicationType,
    LenientRepositoryType,
    MeetingType,
)

if TYPE_CHECKING:
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


def _format_parse_error(
    model_name: str, error: ValidationError, obj: Any = None
) -> str:
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
    for i, err in enumerate(errors, 1):
        loc_tuple: tuple[str | int, ...] = err.get("loc", ())
        loc = _format_loc(loc_tuple)
        msg = err.get("msg", "unknown error")
        input_val = err.get("input")
        context = _extract_context(obj, loc_tuple) if obj is not None else None
        line = f"  {i}. {loc}: {msg}"
        if context:
            line += f" [{context}]"
        if input_val is not None and not isinstance(input_val, dict | list):
            line += f" [got: {type(input_val).__name__} = {input_val!r}]"
        lines.append(line)
    return "\n".join(lines)


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
        **kwargs: Any,
    ) -> Self:
        try:
            return super().model_validate(obj, *args, **kwargs)
        except ValidationError as exc:
            raise ResponseParseError(
                _format_parse_error(cls.__name__, exc, obj=obj), raw_data=obj
            ) from exc


class Link(_Base):
    """A labelled URL, optionally rendered as a Rich clickable hyperlink."""

    label: str | None = None
    url: str | None = None

    def __rich__(self) -> Text:
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

    is_contact_editor: str | None = None


class EditorialBoardMember(Person):
    """A member of a publication editorial board."""

    is_chair: bool | None = None
    is_ex_officio: bool | None = None


class AnalysisContact(Person):
    """An analysis contact with a start/end assignment period."""

    start_date: datetime | None = None
    end_date: datetime | None = None


class Groups(_Base):
    """Leading group, subgroups, and other groups for a publication."""

    leading_group: str | None = None
    subgroups: list[str] = Field(default_factory=list)
    other_groups: list[str] = Field(default_factory=list)


class Collision(_Base):
    """A collision dataset descriptor (centre-of-mass energy, luminosity, etc.)."""

    type: LenientCollisionType | None = None
    year: str | None = None
    run: str | None = None
    ecm_value: str | None = None
    ecm_unit: str | None = None
    luminosity_value: str | None = None
    luminosity_unit: str | None = None


class Metadata(_Base):
    """Physics and technical metadata shared across resource types.

    Not all fields are populated for every resource type; absent fields are None.
    """

    collisions: list[Collision] = Field(default_factory=list)
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
        if isinstance(data, dict) and isinstance(data.get("link"), str):
            link_url = data.pop("link", None)
            link_label = data.pop("linkLabel", None)
            if link_url is not None or link_label is not None:
                data["link"] = {"label": link_label, "url": link_url}
        return data


class TypedMeeting(Meeting):
    """A Meeting tagged with its phase0 role (EOI, EB request, pre-approval, approval)."""

    meeting_type: MeetingType


class RelatedPublication(_Base):
    """A reference to a related publication (analysis, paper, CONF/PUB note)."""

    reference_code: str | None = None
    type: LenientPublicationType | None = None

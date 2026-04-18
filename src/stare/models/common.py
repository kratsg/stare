"""Shared pydantic models reused across all Glance resource types."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pydantic.alias_generators import to_camel

from stare.exceptions import ResponseParseError

if TYPE_CHECKING:
    from typing import Any

    from typing_extensions import Self


def _format_parse_error(model_name: str, error: ValidationError) -> str:
    """Build a human-readable summary of a pydantic ValidationError.

    For scalar inputs the offending value is shown inline; complex inputs
    (dicts/lists) are omitted from the line to keep the output concise — the
    caller may display the full raw payload separately.
    """
    errors = error.errors()
    count = len(errors)
    lines = [
        f"Failed to parse {model_name} from API response ({count} validation error(s)):"
    ]
    for i, err in enumerate(errors, 1):
        loc = ".".join(str(p) for p in err.get("loc", ())) or "(root)"
        msg = err.get("msg", "unknown error")
        input_val = err.get("input")
        if input_val is not None and not isinstance(input_val, (dict, list)):
            lines.append(
                f"  {i}. {loc}: {msg} [got: {type(input_val).__name__} = {input_val!r}]"
            )
        else:
            lines.append(f"  {i}. {loc}: {msg}")
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
                _format_parse_error(cls.__name__, exc), raw_data=obj
            ) from exc


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

    start_date: str | None = None
    end_date: str | None = None


class Groups(_Base):
    """Leading group, subgroups, and other groups for a publication."""

    leading_group: str | None = None
    subgroups: list[str] = Field(default_factory=list)
    other_groups: list[str] = Field(default_factory=list)


class Collision(_Base):
    """A collision dataset descriptor (centre-of-mass energy, luminosity, etc.)."""

    type: str | None = None
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


class Repository(_Base):
    """A code or documentation repository."""

    gitlab_id: str | None = None
    label: str | None = None
    type: str | None = None
    url: str | None = None


class InternalDocument(_Base):
    """A supporting internal document (e.g. CDS note)."""

    label: str | None = None
    url: str | None = None


class Documentation(_Base):
    """Repositories and supporting documents for a publication."""

    repositories: list[Repository] = Field(default_factory=list)
    supporting_internal_documents: list[InternalDocument] = Field(default_factory=list)


class Meeting(_Base):
    """A recorded meeting (EOI, editorial board request, pre-approval, approval, etc.)."""

    title: str | None = None
    date: str | None = None
    comments: str | None = None
    link_label: str | None = None
    link: str | None = None


class AmiGlanceLink(_Base):
    """An AMI/Glance cross-reference link."""

    label: str | None = None
    url: str | None = None


class RelatedPublication(_Base):
    """A reference to a related publication (analysis, paper, CONF/PUB note)."""

    reference_code: str | None = None
    type: str | None = None

"""Shared pydantic models reused across all Glance resource types."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, ValidationError

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
    model_config = ConfigDict(populate_by_name=True)

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

    cern_ccid: str | None = Field(default=None, alias="cernCcid")
    first_name: str | None = Field(default=None, alias="firstName")
    last_name: str | None = Field(default=None, alias="lastName")
    email: str | None = Field(default=None, alias="email")


class TeamMember(Person):
    """A member of an analysis team."""

    is_contact_editor: str | None = Field(default=None, alias="isContactEditor")


class EditorialBoardMember(Person):
    """A member of a publication editorial board."""

    is_chair: bool | None = Field(default=None, alias="isChair")
    is_ex_officio: bool | None = Field(default=None, alias="isExOfficio")


class AnalysisContact(Person):
    """An analysis contact with a start/end assignment period."""

    start_date: str | None = Field(default=None, alias="startDate")
    end_date: str | None = Field(default=None, alias="endDate")


class Groups(_Base):
    """Leading group, subgroups, and other groups for a publication."""

    leading_group: str | None = Field(default=None, alias="leadingGroup")
    subgroups: list[str] | None = Field(default=None, alias="subgroups")
    other_groups: list[str] | None = Field(default=None, alias="otherGroups")


class Collision(_Base):
    """A collision dataset descriptor (centre-of-mass energy, luminosity, etc.)."""

    type: str | None = Field(default=None, alias="type")
    year: str | None = Field(default=None, alias="year")
    run: str | None = Field(default=None, alias="run")
    ecm_value: str | None = Field(default=None, alias="ecmValue")
    ecm_unit: str | None = Field(default=None, alias="ecmUnit")
    luminosity_value: str | None = Field(default=None, alias="luminosityValue")
    luminosity_unit: str | None = Field(default=None, alias="luminosityUnit")


class Metadata(_Base):
    """Physics and technical metadata shared across resource types.

    Not all fields are populated for every resource type; absent fields are None.
    """

    collisions: list[Collision] | None = Field(default=None, alias="collisions")
    keywords: list[str] | None = Field(default=None, alias="keywords")
    statistical_tools: list[str] | None = Field(default=None, alias="statisticalTools")
    mva_ml_tools: list[str] | None = Field(default=None, alias="mvaMlTools")
    triggers: list[str] | None = Field(default=None, alias="triggers")
    # Analysis-specific
    analysis_frameworks: dict[str, list[str]] | None = Field(
        default=None, alias="analysisFrameworks"
    )
    # Paper-specific
    rivet_routines: list[str] | None = Field(default=None, alias="rivetRoutines")


class Repository(_Base):
    """A code or documentation repository."""

    gitlab_id: str | None = Field(default=None, alias="gitlabId")
    label: str | None = Field(default=None, alias="label")
    type: str | None = Field(default=None, alias="type")
    url: str | None = Field(default=None, alias="url")


class InternalDocument(_Base):
    """A supporting internal document (e.g. CDS note)."""

    label: str | None = Field(default=None, alias="label")
    url: str | None = Field(default=None, alias="url")


class Documentation(_Base):
    """Repositories and supporting documents for a publication."""

    repositories: list[Repository] = Field(default_factory=list, alias="repositories")
    supporting_internal_documents: list[InternalDocument] = Field(
        default_factory=list, alias="supportingInternalDocuments"
    )


class Meeting(_Base):
    """A recorded meeting (EOI, editorial board request, pre-approval, approval, etc.)."""

    title: str | None = Field(default=None, alias="title")
    date: str | None = Field(default=None, alias="date")
    comments: str | None = Field(default=None, alias="comments")
    link_label: str | None = Field(default=None, alias="linkLabel")
    link: str | None = Field(default=None, alias="link")


class AmiGlanceLink(_Base):
    """An AMI/Glance cross-reference link."""

    label: str | None = Field(default=None, alias="label")
    url: str | None = Field(default=None, alias="url")


class RelatedPublication(_Base):
    """A reference to a related publication (analysis, paper, CONF/PUB note)."""

    reference_code: str | None = Field(default=None, alias="referenceCode")
    type: str | None = Field(default=None, alias="type")

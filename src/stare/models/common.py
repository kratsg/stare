"""Shared pydantic models reused across all Glance resource types."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


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

    leading_group: list[str] | None = Field(default=None, alias="leadingGroup")
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

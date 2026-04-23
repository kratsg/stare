"""Glance client with resource accessors for the ATLAS Glance/Fence API."""

from __future__ import annotations

import ssl
from importlib.resources import as_file, files
from typing import TYPE_CHECKING, Any, TypeVar

import httpx
from hishel import CacheOptions, SpecificationPolicy, SyncSqliteStorage
from hishel.httpx import SyncCacheTransport
from pydantic import TypeAdapter, ValidationError

from stare.auth import TokenManager
from stare.dsl import Expression, parse_dsl
from stare.dsl.models import Condition, Operator
from stare.exceptions import (
    ApiError,
    ForbiddenError,
    NotFoundError,
    ResponseParseError,
    UnauthorizedError,
)
from stare.models import (
    Analysis,
    AnalysisSearchResult,
    ConfNote,
    ConfNoteSearchResult,
    Paper,
    PaperSearchResult,
    PublicationRef,
    PubNote,
    PubNoteSearchResult,
    Trigger,
)
from stare.settings import StareSettings

_ResourceT = TypeVar("_ResourceT", Analysis, Paper, ConfNote, PubNote)

if TYPE_CHECKING:
    import types
    from collections.abc import Callable

    from stare.models.search import _SearchResultsBase
    from stare.typing import Mode

_BUNDLE_FILE: dict[str, str] = {
    "Sectigo": "Sectigo_chain.pem",
    "CERN": "CERN_chain.pem",
}


def _load_ssl_context(ca_bundle: str) -> ssl.SSLContext:
    """Create an SSLContext from a bundled CA chain.

    Neither the production endpoint (atlas-glance.cern.ch, Sectigo cert) nor
    the staging endpoint (glance-staging01.cern.ch, CERN Grid CA cert) sends
    the full chain in the TLS handshake. The named bundle in stare.data
    provides the missing CA(s) so Python can build the chain. Uses as_file()
    so the resource is available as a real filesystem path inside a wheel.
    """
    filename = _BUNDLE_FILE.get(ca_bundle, f"{ca_bundle}_chain.pem")
    with as_file(files("stare.data").joinpath(filename)) as cert_path:
        return ssl.create_default_context(cafile=str(cert_path))


def _raise_for_status(response: httpx.Response) -> None:
    """Map HTTP error responses to typed stare exceptions."""
    if response.is_success:
        return
    try:
        body = response.json()
    except ValueError:
        body = {}
    if not isinstance(body, dict):
        body = {}
    status_code = response.status_code
    title = str(body.get("title", response.reason_phrase or "Error"))
    detail = str(body.get("detail", ""))
    if status_code == 401:
        raise UnauthorizedError(status_code, title, detail)
    if status_code == 403:
        raise ForbiddenError(status_code, title, detail)
    if status_code == 404:
        raise NotFoundError(status_code, title, detail)
    raise ApiError(status_code, title, detail)


def _resolve_query(
    q: str | Expression,
    *,
    mode: Mode,
    validate: bool,
) -> str:
    if isinstance(q, str):
        return parse_dsl(q, mode=mode).to_dsl() if validate else q
    return q.to_dsl()


def _get_by_ref(
    search: Callable[..., _SearchResultsBase[_ResourceT]],
    *,
    field: str,
    ref_code: str,
    verbose: bool,
) -> _ResourceT:
    """Delegate ``.get(ref_code)`` to ``.search()`` via the DSL.

    Builds a single ``Condition`` (never a string) so future DSL changes flow
    through without touching callers. Raises ``NotFoundError`` on zero results.
    """
    condition = Condition(field=field, operator=Operator.EQ, value=ref_code)
    result = search(query=condition, limit=1, verbose=verbose)
    if not result.results:
        raise NotFoundError(0, "Not Found", f"{field}={ref_code!r} not found")
    return result.results[0]


class AnalysisResource:
    """Accessor for /analyses/ and /searchAnalysis endpoints."""

    def __init__(self, client: httpx.Client) -> None:
        """Store the shared httpx client."""
        self._client = client

    def get(self, ref_code: str, *, verbose: bool = False) -> Analysis:
        """Fetch a single analysis by reference code via /searchAnalysis."""
        return _get_by_ref(
            self.search, field="referenceCode", ref_code=ref_code, verbose=verbose
        )

    def search(
        self,
        *,
        query: str | Expression | None = None,
        offset: int = 0,
        limit: int = 50,
        sort_by: str | None = None,
        sort_desc: bool = False,
        validate_query: bool = True,
        verbose: bool = False,
    ) -> AnalysisSearchResult:
        """Search analyses via GET /searchAnalysis."""
        params: dict[str, Any] = {"offset": offset, "limit": limit}
        if query is not None:
            params["queryString"] = _resolve_query(
                query, mode="analysis", validate=validate_query
            )
        if sort_by is not None:
            params["sortBy"] = sort_by
            params["sortDesc"] = str(sort_desc).lower()
        response = self._client.get("/searchAnalysis", params=params)
        _raise_for_status(response)
        return AnalysisSearchResult.model_validate(response.json(), verbose=verbose)


class PaperResource:
    """Accessor for /papers/ and /searchPaper endpoints."""

    def __init__(self, client: httpx.Client) -> None:
        """Store the shared httpx client."""
        self._client = client

    def get(self, ref_code: str, *, verbose: bool = False) -> Paper:
        """Fetch a single paper by reference code via /searchPaper."""
        return _get_by_ref(
            self.search, field="referenceCode", ref_code=ref_code, verbose=verbose
        )

    def search(
        self,
        *,
        query: str | Expression | None = None,
        offset: int = 0,
        limit: int = 50,
        sort_by: str | None = None,
        sort_desc: bool = False,
        validate_query: bool = True,
        verbose: bool = False,
    ) -> PaperSearchResult:
        """Search papers via GET /searchPaper."""
        params: dict[str, Any] = {"offset": offset, "limit": limit}
        if query is not None:
            params["queryString"] = _resolve_query(
                query, mode="paper", validate=validate_query
            )
        if sort_by is not None:
            params["sortBy"] = sort_by
            params["sortDesc"] = str(sort_desc).lower()
        response = self._client.get("/searchPaper", params=params)
        _raise_for_status(response)
        return PaperSearchResult.model_validate(response.json(), verbose=verbose)


class ConfNoteResource:
    """Accessor for /confnotes/ endpoint."""

    def __init__(self, client: httpx.Client) -> None:
        """Store the shared httpx client."""
        self._client = client

    def get(self, ref_code: str, *, verbose: bool = False) -> ConfNote:
        """Fetch a single CONF note by temporary reference code via /searchConfnote."""
        return _get_by_ref(
            self.search, field="temporaryReferenceCode", ref_code=ref_code, verbose=verbose
        )

    def search(
        self,
        *,
        query: str | Expression | None = None,
        offset: int = 0,
        limit: int = 50,
        sort_by: str | None = None,
        sort_desc: bool = False,
        validate_query: bool = True,
        verbose: bool = False,
    ) -> ConfNoteSearchResult:
        """Search conf notes via GET /searchConfNote."""
        params: dict[str, Any] = {"offset": offset, "limit": limit}
        if query is not None:
            params["queryString"] = _resolve_query(
                query, mode="confnote", validate=validate_query
            )
        if sort_by is not None:
            params["sortBy"] = sort_by
            params["sortDesc"] = str(sort_desc).lower()
        response = self._client.get("/searchConfnote", params=params)
        _raise_for_status(response)
        return ConfNoteSearchResult.model_validate(response.json(), verbose=verbose)


class PubNoteResource:
    """Accessor for /searchPubnote endpoint."""

    def __init__(self, client: httpx.Client) -> None:
        """Store the shared httpx client."""
        self._client = client

    def get(self, ref_code: str, *, verbose: bool = False) -> PubNote:
        """Fetch a single PUB note by temporary reference code via /searchPubnote."""
        return _get_by_ref(
            self.search, field="temporaryReferenceCode", ref_code=ref_code, verbose=verbose
        )

    def search(
        self,
        *,
        query: str | Expression | None = None,
        offset: int = 0,
        limit: int = 50,
        sort_by: str | None = None,
        sort_desc: bool = False,
        validate_query: bool = True,
        verbose: bool = False,
    ) -> PubNoteSearchResult:
        """Search pub notes via GET /searchPubnote."""
        params: dict[str, Any] = {"offset": offset, "limit": limit}
        if query is not None:
            params["queryString"] = _resolve_query(
                query, mode="pubnote", validate=validate_query
            )
        if sort_by is not None:
            params["sortBy"] = sort_by
            params["sortDesc"] = str(sort_desc).lower()
        response = self._client.get("/searchPubnote", params=params)
        _raise_for_status(response)
        return PubNoteSearchResult.model_validate(response.json(), verbose=verbose)


class PublicationResource:
    """Accessor for /publications/search endpoint."""

    def __init__(self, client: httpx.Client) -> None:
        """Store the shared httpx client."""
        self._client = client

    def search(
        self,
        *,
        reference_codes: list[str] | None = None,
        types: list[str] | None = None,
        short_titles: list[str] | None = None,
        leading_groups: list[str] | None = None,
        subgroups: list[str] | None = None,
        statuses: list[str] | None = None,
        verbose: bool = False,
    ) -> list[PublicationRef]:
        """Search across all publication types."""
        params: list[tuple[str, str | int | float | bool | None]] = []
        params += [("referenceCodes", val) for val in reference_codes or []]
        params += [("types", val) for val in types or []]
        params += [("shortTitles", val) for val in short_titles or []]
        params += [("leadingGroups", val) for val in leading_groups or []]
        params += [("subgroups", val) for val in subgroups or []]
        params += [("statuses", val) for val in statuses or []]
        response = self._client.get("/publications/search", params=params)
        _raise_for_status(response)
        return [
            PublicationRef.model_validate(item, verbose=verbose)
            for item in response.json()
        ]


class GroupResource:
    """Accessor for /groups endpoint."""

    def __init__(self, client: httpx.Client) -> None:
        """Store the shared httpx client."""
        self._client = client

    def list(self) -> list[str]:
        """List all leading groups."""
        response = self._client.get("/groups")
        _raise_for_status(response)
        try:
            return TypeAdapter(list[str]).validate_python(response.json())
        except ValidationError as exc:
            raise ResponseParseError(str(exc), raw_data=response.json()) from exc


class SubgroupResource:
    """Accessor for /subgroups endpoint."""

    def __init__(self, client: httpx.Client) -> None:
        """Store the shared httpx client."""
        self._client = client

    def list(self) -> list[str]:
        """List all subgroups."""
        response = self._client.get("/subgroups")
        _raise_for_status(response)
        try:
            return TypeAdapter(list[str]).validate_python(response.json())
        except ValidationError as exc:
            raise ResponseParseError(str(exc), raw_data=response.json()) from exc


class TriggerResource:
    """Accessor for /triggers/search endpoint."""

    def __init__(self, client: httpx.Client) -> None:
        """Store the shared httpx client."""
        self._client = client

    def search(
        self,
        *,
        categories: list[str] | None = None,
        years: list[str] | None = None,
        verbose: bool = False,
    ) -> list[Trigger]:
        """Search triggers by category and/or year."""
        params: list[tuple[str, str | int | float | bool | None]] = []
        params += [("categories", val) for val in categories or []]
        params += [("years", val) for val in years or []]
        response = self._client.get("/triggers/search", params=params)
        _raise_for_status(response)
        return [
            Trigger.model_validate(item, verbose=verbose) for item in response.json()
        ]


class Glance:
    """Top-level client for the ATLAS Glance/Fence API."""

    def __init__(
        self,
        *,
        settings: StareSettings | None = None,
        token_manager: TokenManager | None = None,
        token: str | None = None,
    ) -> None:
        """Build the httpx client, attach the cache transport, and wire up resource accessors."""
        self._settings = settings or StareSettings()
        self._token = token
        if token_manager is None and token is None:
            self._token_manager: TokenManager | None = TokenManager(self._settings)
        else:
            self._token_manager = token_manager
        ssl_ctx = _load_ssl_context(self._settings.ca_bundle)
        base_transport = httpx.HTTPTransport(verify=ssl_ctx)
        if self._settings.cache_enabled:
            cache_dir = self._settings.get_cache_dir()
            cache_dir.mkdir(parents=True, exist_ok=True)
            transport: httpx.BaseTransport = SyncCacheTransport(
                next_transport=base_transport,
                storage=SyncSqliteStorage(
                    database_path=cache_dir / "cache.db",
                    default_ttl=float(self._settings.cache_ttl_seconds),
                ),
                policy=SpecificationPolicy(
                    cache_options=CacheOptions(
                        shared=False,
                        supported_methods=["GET"],
                        allow_stale=True,
                    )
                ),
            )
        else:
            transport = base_transport
        self._http = httpx.Client(
            base_url=self._settings.base_url,
            transport=transport,
            event_hooks={"request": [self._inject_auth]},
        )
        self.analyses = AnalysisResource(self._http)
        self.papers = PaperResource(self._http)
        self.confnotes = ConfNoteResource(self._http)
        self.pubnotes = PubNoteResource(self._http)
        self.publications = PublicationResource(self._http)
        self.groups = GroupResource(self._http)
        self.subgroups = SubgroupResource(self._http)
        self.triggers = TriggerResource(self._http)

    def _inject_auth(self, request: httpx.Request) -> None:
        token = self._token or (
            self._token_manager.get_token() if self._token_manager else None
        )
        if token:
            request.headers["Authorization"] = f"Bearer {token}"
        else:
            request.headers.pop("Authorization", None)

    def __enter__(self) -> Glance:
        """Enter the context manager, opening the underlying HTTP connection."""
        self._http.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Exit the context manager, closing the underlying HTTP connection."""
        self._http.__exit__(exc_type, exc_val, exc_tb)

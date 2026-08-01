"""Glance client with resource accessors for the ATLAS Glance/Fence API."""

from __future__ import annotations

import ssl
from importlib.resources import as_file, files
from typing import TYPE_CHECKING, Any, ClassVar, Generic, TypeVar, cast

import httpx
from hishel import CacheOptions, SpecificationPolicy, SyncSqliteStorage
from hishel.httpx import SyncCacheTransport

from stare._version import version as __version__
from stare.auth import TokenManager
from stare.dsl import Expression, parse_dsl
from stare.dsl.models import Condition, Operator
from stare.exceptions import (
    ApiError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
)
from stare.models import (
    Analysis,
    AnalysisSearchResult,
    ConfNote,
    ConfNoteSearchResult,
    Paper,
    PaperSearchResult,
    Plot,
    PlotSearchResult,
    PublicationSearchResult,
    PublicationSummary,
    PubNote,
    PubNoteSearchResult,
)
from stare.models.search import (
    LeadingGroupSearchResult,
    SubgroupSearchResult,
    TriggerSearchResult,
)
from stare.settings import StareSettings

_SearchResultT = TypeVar("_SearchResultT", bound="_SearchResultsBase[Any]")
_ItemT = TypeVar("_ItemT")

if TYPE_CHECKING:
    import types

    from stare.models.search import _SearchResultsBase
    from stare.typing import Mode

_BUNDLE_FILE: dict[str, str] = {
    "Sectigo": "Sectigo_chain.pem",
    "CERN": "CERN_chain.pem",
}


def _load_ssl_context(ca_bundle: str) -> ssl.SSLContext:
    """Create an SSLContext from a bundled CA chain plus the system trust store.

    Neither the production endpoint (atlas-glance.cern.ch, Sectigo cert) nor
    the staging endpoint (glance-staging01.cern.ch, CERN Grid CA cert) sends
    the full chain in the TLS handshake. The named bundle in stare.data
    provides the missing CA(s) so Python can build the chain. Uses as_file()
    so the resource is available as a real filesystem path inside a wheel.
    Also loading the system default certs means a server-side CA rotation
    degrades gracefully instead of breaking every installed client until a
    release ships an updated bundle.
    """
    filename = _BUNDLE_FILE.get(ca_bundle, f"{ca_bundle}_chain.pem")
    with as_file(files("stare.data").joinpath(filename)) as cert_path:
        ctx = ssl.create_default_context(cafile=str(cert_path))
    ctx.load_default_certs()
    return ctx


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


class _Resource(Generic[_SearchResultT]):
    """Generic search accessor parameterized by endpoint, DSL mode, and result model."""

    _endpoint: ClassVar[str]
    _mode: ClassVar[Mode]
    _result_model: type[_SearchResultT]

    def __init__(self, client: httpx.Client) -> None:
        """Store the shared httpx client."""
        self._client = client

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
    ) -> _SearchResultT:
        """Search this resource's endpoint with an optional DSL query."""
        params: dict[str, Any] = {"offset": offset, "limit": limit}
        if query is not None:
            params["queryString"] = _resolve_query(
                query, mode=self._mode, validate=validate_query
            )
        if sort_by is not None:
            params["sortBy"] = sort_by
            params["sortDesc"] = str(sort_desc).lower()
        response = self._client.get(self._endpoint, params=params)
        _raise_for_status(response)
        return self._result_model.model_validate(response.json(), verbose=verbose)


class _GettableResource(_Resource[_SearchResultT], Generic[_SearchResultT, _ItemT]):
    """A search resource that also resolves a single record by reference code."""

    _get_field: ClassVar[str]

    def get(self, ref_code: str, *, verbose: bool = False) -> _ItemT:
        """Fetch a single record by reference code via this resource's search endpoint.

        Builds a single ``Condition`` (never a string) so future DSL changes flow
        through without touching callers. Raises ``NotFoundError`` on zero results.
        """
        condition = Condition(
            field=self._get_field, operator=Operator.EQ, value=ref_code
        )
        result = self.search(query=condition, limit=1, verbose=verbose)
        if not result.results:
            raise NotFoundError(
                404, "Not Found", f"{self._get_field}={ref_code!r} not found"
            )
        return cast("_ItemT", result.results[0])


class AnalysisResource(_GettableResource[AnalysisSearchResult, Analysis]):
    """Accessor for /analyses/ and /searchAnalysis endpoints."""

    _endpoint = "/searchAnalysis"
    _mode = "analysis"
    _result_model = AnalysisSearchResult
    _get_field = "referenceCode"


class PaperResource(_GettableResource[PaperSearchResult, Paper]):
    """Accessor for /papers/ and /searchPaper endpoints."""

    _endpoint = "/searchPaper"
    _mode = "paper"
    _result_model = PaperSearchResult
    _get_field = "referenceCode"


class ConfNoteResource(_GettableResource[ConfNoteSearchResult, ConfNote]):
    """Accessor for /confnotes/ endpoint."""

    _endpoint = "/searchConfnote"
    _mode = "confnote"
    _result_model = ConfNoteSearchResult
    _get_field = "temporaryReferenceCode"


class PubNoteResource(_GettableResource[PubNoteSearchResult, PubNote]):
    """Accessor for /searchPubnote endpoint."""

    _endpoint = "/searchPubnote"
    _mode = "pubnote"
    _result_model = PubNoteSearchResult
    _get_field = "temporaryReferenceCode"


class PlotResource(_GettableResource[PlotSearchResult, Plot]):
    """Accessor for /searchPlot endpoint."""

    _endpoint = "/searchPlot"
    _mode = "plot"
    _result_model = PlotSearchResult
    _get_field = "referenceCode"


class PublicationResource(_Resource[PublicationSearchResult]):
    """Accessor for the /searchPublication endpoint."""

    _endpoint = "/searchPublication"
    _mode = "publication"
    _result_model = PublicationSearchResult

    def get(self, ref_code: str, *, verbose: bool = False) -> PublicationSummary:
        """Fetch a single publication by reference code via /searchPublication."""
        for field in ("referenceCode", "temporaryReferenceCode", "finalReferenceCode"):
            condition = Condition(field=field, operator=Operator.EQ, value=ref_code)
            result = self.search(query=condition, limit=1, verbose=verbose)
            if result.results:
                return result.results[0]
        raise NotFoundError(404, "Not Found", f"{ref_code!r} not found")


class LeadingGroupResource(_Resource[LeadingGroupSearchResult]):
    """Accessor for /searchLeadingGroup endpoint."""

    _endpoint = "/searchLeadingGroup"
    _mode = "leadinggroup"
    _result_model = LeadingGroupSearchResult


class SubgroupResource(_Resource[SubgroupSearchResult]):
    """Accessor for /searchSubgroup endpoint."""

    _endpoint = "/searchSubgroup"
    _mode = "subgroup"
    _result_model = SubgroupSearchResult


class TriggerResource(_Resource[TriggerSearchResult]):
    """Accessor for /searchTrigger endpoint."""

    _endpoint = "/searchTrigger"
    _mode = "trigger"
    _result_model = TriggerSearchResult


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
            headers={"user-agent": f"stare/{__version__}"},
        )
        self.analyses = AnalysisResource(self._http)
        self.papers = PaperResource(self._http)
        self.confnotes = ConfNoteResource(self._http)
        self.pubnotes = PubNoteResource(self._http)
        self.plots = PlotResource(self._http)
        self.publications = PublicationResource(self._http)
        self.leadinggroups = LeadingGroupResource(self._http)
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

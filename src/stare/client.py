"""Glance client with resource accessors for the ATLAS Glance/Fence API."""

from __future__ import annotations

import ssl
from importlib.resources import as_file, files
from typing import TYPE_CHECKING, Any

import httpx
from hishel import CacheOptions, SpecificationPolicy, SyncSqliteStorage
from hishel.httpx import SyncCacheTransport

from stare.auth import TokenManager
from stare.exceptions import ApiError, ForbiddenError, NotFoundError, UnauthorizedError
from stare.models import (
    Analysis,
    AnalysisSearchResult,
    ConfNote,
    Paper,
    PaperSearchResult,
    PublicationRef,
    PubNote,
    Trigger,
)
from stare.settings import StareSettings

if TYPE_CHECKING:
    import types

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
        body: dict[str, Any] = response.json()
    except ValueError:
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


class AnalysisResource:
    """Accessor for /analyses/ and /searchAnalysis endpoints."""

    def __init__(self, client: httpx.Client) -> None:
        """Store the shared httpx client."""
        self._client = client

    def get(self, ref_code: str) -> Analysis:
        """Fetch a single analysis by reference code."""
        response = self._client.get(f"/analyses/{ref_code}")
        _raise_for_status(response)
        return Analysis.model_validate(response.json())

    def search(
        self,
        *,
        query: str | None = None,
        offset: int = 0,
        limit: int = 50,
        sort_by: str | None = None,
        sort_desc: bool = False,
    ) -> AnalysisSearchResult:
        """Search analyses via GET /searchAnalysis."""
        params: dict[str, Any] = {"offset": offset, "limit": limit}
        if query is not None:
            params["queryString"] = query
        if sort_by is not None:
            params["sortBy"] = sort_by
            params["sortDesc"] = str(sort_desc).lower()
        response = self._client.get("/searchAnalysis", params=params)
        _raise_for_status(response)
        return AnalysisSearchResult.model_validate(response.json())


class PaperResource:
    """Accessor for /papers/ and /searchPaper endpoints."""

    def __init__(self, client: httpx.Client) -> None:
        """Store the shared httpx client."""
        self._client = client

    def get(self, ref_code: str) -> Paper:
        """Fetch a single paper by reference code."""
        response = self._client.get(f"/papers/{ref_code}")
        _raise_for_status(response)
        return Paper.model_validate(response.json())

    def search(
        self,
        *,
        query: str | None = None,
        offset: int = 0,
        limit: int = 50,
        sort_by: str | None = None,
        sort_desc: bool = False,
    ) -> PaperSearchResult:
        """Search papers via GET /searchPaper."""
        params: dict[str, Any] = {"offset": offset, "limit": limit}
        if query is not None:
            params["queryString"] = query
        if sort_by is not None:
            params["sortBy"] = sort_by
            params["sortDesc"] = str(sort_desc).lower()
        response = self._client.get("/searchPaper", params=params)
        _raise_for_status(response)
        return PaperSearchResult.model_validate(response.json())


class ConfNoteResource:
    """Accessor for /confnotes/ endpoint."""

    def __init__(self, client: httpx.Client) -> None:
        """Store the shared httpx client."""
        self._client = client

    def get(self, temp_ref_code: str) -> ConfNote:
        """Fetch a single CONF note by temporary reference code."""
        response = self._client.get(f"/confnotes/{temp_ref_code}")
        _raise_for_status(response)
        return ConfNote.model_validate(response.json())


class PubNoteResource:
    """Accessor for /pubnotes/ endpoint."""

    def __init__(self, client: httpx.Client) -> None:
        """Store the shared httpx client."""
        self._client = client

    def get(self, temp_ref_code: str) -> PubNote:
        """Fetch a single PUB note by temporary reference code."""
        response = self._client.get(f"/pubnotes/{temp_ref_code}")
        _raise_for_status(response)
        return PubNote.model_validate(response.json())


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
        return [PublicationRef.model_validate(item) for item in response.json()]


class GroupResource:
    """Accessor for /groups endpoint."""

    def __init__(self, client: httpx.Client) -> None:
        """Store the shared httpx client."""
        self._client = client

    def list(self) -> list[str]:
        """List all leading groups."""
        response = self._client.get("/groups")
        _raise_for_status(response)
        return list(response.json())


class SubgroupResource:
    """Accessor for /subgroups endpoint."""

    def __init__(self, client: httpx.Client) -> None:
        """Store the shared httpx client."""
        self._client = client

    def list(self) -> list[str]:
        """List all subgroups."""
        response = self._client.get("/subgroups")
        _raise_for_status(response)
        return list(response.json())


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
    ) -> list[Trigger]:
        """Search triggers by category and/or year."""
        params: list[tuple[str, str | int | float | bool | None]] = []
        params += [("categories", val) for val in categories or []]
        params += [("years", val) for val in years or []]
        response = self._client.get("/triggers/search", params=params)
        _raise_for_status(response)
        return [Trigger.model_validate(item) for item in response.json()]


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
        self._token_manager = token_manager or TokenManager(self._settings)
        self._token = token
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
        self.conf_notes = ConfNoteResource(self._http)
        self.pub_notes = PubNoteResource(self._http)
        self.publications = PublicationResource(self._http)
        self.groups = GroupResource(self._http)
        self.subgroups = SubgroupResource(self._http)
        self.triggers = TriggerResource(self._http)

    def _inject_auth(self, request: httpx.Request) -> None:
        token = self._token or self._token_manager.get_token()
        request.headers["Authorization"] = f"Bearer {token}"

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

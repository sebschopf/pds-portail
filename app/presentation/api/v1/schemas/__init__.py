"""Schemas Pydantic pour les endpoints de recherche et détail dataset.

Normalisent et enrichissent les réponses CKAN via les indicateurs de qualité
et la structure dataset explicitée.

ADR-035 : contrats stricts pour les DTOs cœur de l'interface utilisateur
(SearchDatasetItem, CompareItem, DatasetDetailResponse). Les schémas internes
conservent leurs valeurs par défaut pour ne pas impacter les adaptateurs
sans bénéfice frontend.
"""

from app.presentation.api.v1.schemas.compare import (
    MAX_COMPARE_IDS,
    CompareItem,
    CompareRequest,
    CompareResponse,
)
from app.presentation.api.v1.schemas.dataset import (
    AccessMode,
    ColumnInfo,
    ColumnStats,
    DatasetDetailResponse,
    DatasetStructure,
    ExploreResourceResponse,
    ResourceAnalysis,
    ResourceDetailResponse,
    ResourceResponse,
)
from app.presentation.api.v1.schemas.internal import (
    CacheCountsResponse,
    CacheStatsResponse,
    ContactRequest,
    HealthResponse,
    InternalCacheResponse,
    InternalSupportEmailDeliverabilityResponse,
    InternalSupportMagicLinkResendRequest,
    InternalSupportMagicLinkResendResponse,
    InternalSupportMagicLinkStateResponse,
    InternalSupportSubscriptionResponse,
    InternalSupportWatcherLookupResponse,
    InternalSupportWebhookEventResponse,
    InternalSupportWebhookEventsResponse,
    SyncMetricsItem,
    SyncMetricsResponse,
    SyncStatusResponse,
)
from app.presentation.api.v1.schemas.search import (
    FacetItem,
    RankingSignals,
    SearchDatasetItem,
    SearchFacets,
    SearchResponse,
    TopQueriesResponse,
    TopQueryItem,
    ZeroResultItem,
    ZeroResultsResponse,
)
from app.presentation.api.v1.schemas.watchers import (
    AlertItemResponse,
    AlertsResponse,
    MagicLinkConsumeResponse,
    MagicLinkRequestBody,
    WatchedDatasetItemResponse,
    WatcherCreateRequest,
    WatcherCreateResponse,
    WatchersListResponse,
)

__all__ = [
    # search
    "FacetItem",
    "RankingSignals",
    "SearchDatasetItem",
    "SearchFacets",
    "SearchResponse",
    "TopQueriesResponse",
    "TopQueryItem",
    "ZeroResultItem",
    "ZeroResultsResponse",
    # compare
    "MAX_COMPARE_IDS",
    "CompareItem",
    "CompareRequest",
    "CompareResponse",
    # dataset
    "AccessMode",
    "ColumnInfo",
    "ColumnStats",
    "DatasetDetailResponse",
    "DatasetStructure",
    "ExploreResourceResponse",
    "ResourceAnalysis",
    "ResourceDetailResponse",
    "ResourceResponse",
    # watchers
    "AlertItemResponse",
    "AlertsResponse",
    "MagicLinkConsumeResponse",
    "MagicLinkRequestBody",
    "WatchedDatasetItemResponse",
    "WatcherCreateRequest",
    "WatcherCreateResponse",
    "WatchersListResponse",
    # internal
    "CacheCountsResponse",
    "CacheStatsResponse",
    "ContactRequest",
    "HealthResponse",
    "InternalCacheResponse",
    "InternalSupportEmailDeliverabilityResponse",
    "InternalSupportMagicLinkResendRequest",
    "InternalSupportMagicLinkResendResponse",
    "InternalSupportMagicLinkStateResponse",
    "InternalSupportSubscriptionResponse",
    "InternalSupportWatcherLookupResponse",
    "InternalSupportWebhookEventResponse",
    "InternalSupportWebhookEventsResponse",
    "SyncMetricsItem",
    "SyncMetricsResponse",
    "SyncStatusResponse",
]

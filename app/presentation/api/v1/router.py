import logging
from typing import Literal

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel

from app.application.use_cases.cached_get_dataset_detail import CachedGetDatasetDetailUseCase
from app.application.use_cases.cached_search_datasets import CachedSearchDatasetsUseCase
from app.application.use_cases.compare_datasets import (
    CompareDatasetsUseCase,
    InvalidCompareRequestError,
)
from app.application.use_cases.get_dataset_detail import GetDatasetDetailUseCase
from app.application.use_cases.get_health_status import GetHealthStatusUseCase
from app.application.use_cases.get_resource_detail import GetResourceDetailUseCase
from app.application.use_cases.invalidate_cache_after_sync import invalidate_cache_after_sync
from app.application.use_cases.run_sync_cycle import RunSyncCycleUseCase
from app.application.use_cases.search_datasets import SearchDatasetsUseCase
from app.core.config import get_settings
from app.infrastructure.external.ckan.client import CkanHttpClient
from app.infrastructure.persistence.cache_read_repository import SqlAlchemyCacheReadRepository
from app.infrastructure.persistence.cache_repository import SqlAlchemyCacheRepository
from app.infrastructure.persistence.query_cache_repository import SqlAlchemyQueryCacheRepository
from app.infrastructure.persistence.search_repository import SqlAlchemySearchRepository
from app.presentation.api.v1.schemas import (
    CompareRequest,
    CompareResponse,
    DatasetDetailResponse,
    ResourceDetailResponse,
    SearchResponse,
)

logger = logging.getLogger(__name__)

api_router = APIRouter(prefix="/api/v1")


class HealthResponse(BaseModel):
    """Reponse minimale de sante service/cache."""

    status: str
    last_sync: str | None


class CacheCountsResponse(BaseModel):
    """Compteurs minimaux du cache."""

    organizations: int
    datasets: int
    resources: int


class InternalCacheResponse(BaseModel):
    """Vue interne pour verifier qu'un cache peuple est consultable."""

    status: str
    last_sync: str | None
    cache_populated: bool
    counts: CacheCountsResponse


@api_router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Expose l'etat du service et le dernier horodatage de synchronisation."""

    snapshot = GetHealthStatusUseCase(SqlAlchemyCacheReadRepository()).execute()
    return HealthResponse(status=snapshot.status, last_sync=snapshot.last_sync)


@api_router.get("/internal/cache", response_model=InternalCacheResponse)
def internal_cache_status() -> InternalCacheResponse:
    """Lecture interne minimale pour verifier que le cache est consultable."""

    snapshot = GetHealthStatusUseCase(SqlAlchemyCacheReadRepository()).execute()
    return InternalCacheResponse(
        status=snapshot.status,
        last_sync=snapshot.last_sync,
        cache_populated=snapshot.cache_populated,
        counts=CacheCountsResponse(
            organizations=snapshot.counts.organizations,
            datasets=snapshot.counts.datasets,
            resources=snapshot.counts.resources,
        ),
    )


@api_router.get("/search", response_model=SearchResponse)
def search(
    q: str | None = Query(None, description="Texte libre: titre, description"),
    offset: int = Query(0, ge=0, description="Position de pagination"),
    limit: int = Query(20, ge=1, le=100, description="Resultats par page"),
    org: str | None = Query(None, description="Filtrer par ID organisation"),
    fmt: str | None = Query(None, description="Filtrer par format ressource"),
    tag: str | None = Query(None, description="Filtrer par tag (exact match)"),
    sort: Literal[
        "modified_desc",
        "modified_asc",
        "quality_desc",
        "quality_asc",
        "hybrid",
        "title_asc",
        "title_desc",
    ] = Query("modified_desc", description="Strategie de tri explicite"),
) -> SearchResponse:
    """Recherche les datasets avec pagination et filtres.

    Supporte la recherche full-text sur titre/description ainsi que
    le filtrage par organisation, format de ressource, et tag. Inclut les facettes
    pour construire une interface de recherche facettee.

    Query params:
        q: Texte libre (optionnel)
        offset: Premiere position (defaut 0)
        limit: Resultats par page (1-100, defaut 20)
        org: Filtrer par ID organisation (optionnel)
        fmt: Filtrer par format (CSV, JSON, etc) (optionnel)
        tag: Filtrer par tag specifique (optionnel)
        sort: Strategie de tri explicite

    Returns:
        SearchResponse avec datasets pagines et facettes d'agregation
    """

    settings = get_settings()
    if settings.query_cache_enabled:
        return CachedSearchDatasetsUseCase(
            repository=SqlAlchemySearchRepository(),
            cache=SqlAlchemyQueryCacheRepository(),
            ttl_seconds=settings.query_cache_ttl_seconds,
        ).execute(
            query=q,
            offset=offset,
            limit=limit,
            org_filter=org,
            format_filter=fmt,
            tag_filter=tag,
            sort=sort,
        )
    return SearchDatasetsUseCase(SqlAlchemySearchRepository()).execute(
        query=q,
        offset=offset,
        limit=limit,
        org_filter=org,
        format_filter=fmt,
        tag_filter=tag,
        sort=sort,
    )


@api_router.get("/dataset/{dataset_id}", response_model=DatasetDetailResponse)
def get_dataset(dataset_id: str) -> DatasetDetailResponse:
    """Retourne le detail complet d'un dataset avec ses ressources.

    Inclut les indicateurs de qualite (quality_score, completeness, freshness_days),
    la structure du dataset et les modes d'acces disponibles.

    Path params:
        dataset_id: UUID du dataset CKAN

    Returns:
        DatasetDetailResponse avec detail complet ou 404 si non trouve
    """

    settings = get_settings()
    if settings.query_cache_enabled:
        detail = CachedGetDatasetDetailUseCase(
            repository=SqlAlchemySearchRepository(),
            cache=SqlAlchemyQueryCacheRepository(),
            ttl_seconds=settings.query_cache_ttl_seconds,
        ).execute(dataset_id)
    else:
        detail = GetDatasetDetailUseCase(SqlAlchemySearchRepository()).execute(dataset_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")
    return detail


@api_router.get("/resource/{resource_id}", response_model=ResourceDetailResponse)
def get_resource(resource_id: str) -> ResourceDetailResponse:
    """Retourne le detail d'une ressource avec reference au dataset.

    Path params:
        resource_id: UUID de la ressource CKAN

    Returns:
        ResourceDetailResponse ou 404 si non trouve
    """

    detail = GetResourceDetailUseCase(SqlAlchemySearchRepository()).execute(resource_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Resource {resource_id} not found")
    return detail


@api_router.post("/compare", response_model=CompareResponse)
def compare_datasets(request: CompareRequest) -> CompareResponse:
    """Compare 2 a 4 datasets sur des criteres homogenes (PDS-43).

    Charge les datasets en une seule requete batch et retourne les champs
    comparables : qualite, fraicheur, formats, ressources, tags, etc.

    Body:
        ids: Liste de 2 a 4 IDs de datasets

    Returns:
        CompareResponse avec les items trouves (ordre preserve)

    Raises:
        400: Moins de 2 IDs fournis ou IDs invalides
    """
    try:
        return CompareDatasetsUseCase(SqlAlchemySearchRepository()).execute(request)
    except InvalidCompareRequestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


class SyncStatusResponse(BaseModel):
    """Etat de la synchronisation CKAN incrementale."""

    ckan_offset: int
    updated_at: str | None


@api_router.get("/internal/sync/status", response_model=SyncStatusResponse)
def internal_sync_status() -> SyncStatusResponse:
    """Retourne l'offset courant de la synchronisation CKAN incrementale.

    Permet de superviser la progression du chargement du catalogue
    opendata.swiss (~10 000+ datasets) sans acceder a la base de donnees.
    """
    repository = SqlAlchemyCacheRepository()
    raw_offset = repository.get_sync_state("ckan_offset")
    ckan_offset = int(raw_offset) if raw_offset and raw_offset.isdigit() else 0

    # Recupere l'horodatage via le port repository (ADR-003, PDS-45)
    updated_at = repository.get_sync_state_updated_at("ckan_offset")

    return SyncStatusResponse(ckan_offset=ckan_offset, updated_at=updated_at)


class SyncMetricsItem(BaseModel):
    """Metriques d'un cycle de sync unique (PDS-45)."""

    id: int
    synced_datasets: int
    synced_organizations: int
    synced_resources: int
    errors: int
    mode: str
    duration_ms: int
    started_at: str
    completed_at: str


class SyncMetricsResponse(BaseModel):
    """Historique des metriques d'ingestion (PDS-45)."""

    items: list[SyncMetricsItem]
    total: int


@api_router.get("/internal/sync/metrics", response_model=SyncMetricsResponse)
def internal_sync_metrics(
    limit: int = Query(20, ge=1, le=100, description="Nombre de cycles recents"),
) -> SyncMetricsResponse:
    """Retourne l'historique des metriques d'ingestion CKAN (PDS-45).

    Permet le pilotage du volume, de la duree et des erreurs d'ingestion.
    Les cycles les plus recents apparaissent en premier.

    Query params:
        limit: Nombre de cycles a retourner (1-100, defaut 20)
    """
    from app.infrastructure.persistence.database import SessionLocal
    from app.infrastructure.persistence.models import SyncMetricsModel

    with SessionLocal() as session:
        total = session.query(SyncMetricsModel).count()
        rows = (
            session.query(SyncMetricsModel).order_by(SyncMetricsModel.id.desc()).limit(limit).all()
        )
        items = [
            SyncMetricsItem(
                id=row.id,
                synced_datasets=row.synced_datasets,
                synced_organizations=row.synced_organizations,
                synced_resources=row.synced_resources,
                errors=row.errors,
                mode=row.mode,
                duration_ms=row.duration_ms,
                started_at=row.started_at,
                completed_at=row.completed_at,
            )
            for row in rows
        ]
        return SyncMetricsResponse(items=items, total=total)


@api_router.post("/internal/sync")
def internal_sync_trigger() -> dict[str, str]:
    """Declenche un cycle de synchronisation CKAN immediat (PDS-52).

    Utilise les memes parametres de lot que le scheduler periodique
    (ckan_sync_max_batches_per_run, ckan_sync_batch_rows, etc.).
    Utile pour forcer un rattrapage sans attendre le prochain cycle horaire.

    Returns:
        Message de confirmation avec le timestamp de declenchement.
    """
    settings = get_settings()
    if not settings.enable_ckan_sync:
        raise HTTPException(
            status_code=503, detail="CKAN sync is disabled (ENABLE_CKAN_SYNC=false)"
        )

    from datetime import UTC, datetime

    logger.info("CKAN sync triggered manually via /internal/sync")
    use_case = RunSyncCycleUseCase(
        client=CkanHttpClient(),
        repository=SqlAlchemyCacheRepository(),
        settings=settings,
    )
    metrics = use_case.execute()

    # Invalidation du cache applicatif apres sync (PDS-46)
    invalidate_cache_after_sync(
        cache=SqlAlchemyQueryCacheRepository(),
        synced_count=int(metrics["synced_datasets"]),
    )
    return {"message": "Sync cycle completed", "triggered_at": datetime.now(UTC).isoformat()}


class CacheStatsResponse(BaseModel):
    """Statistiques de hit/miss du cache applicatif (PDS-46)."""

    hits: int
    misses: int
    stale_entries: int
    total_entries: int
    hit_ratio: float


@api_router.get("/internal/cache/stats", response_model=CacheStatsResponse)
def internal_cache_stats() -> CacheStatsResponse:
    """Retourne les statistiques hit/miss du cache applicatif (PDS-46).

    Permet de mesurer le hit-ratio et les gains de latence du cache
    multi-niveaux. Les compteurs sont cumulatifs depuis le dernier
    redemarrage applicatif ou reset explicite.
    """
    cache = SqlAlchemyQueryCacheRepository()
    stats = cache.get_stats()
    return CacheStatsResponse(
        hits=stats.hits,
        misses=stats.misses,
        stale_entries=stats.stale_entries,
        total_entries=stats.total_entries,
        hit_ratio=round(stats.hit_ratio, 4),
    )


@api_router.post("/internal/cache/reset-stats")
def internal_cache_reset_stats(
    x_internal_token: str | None = Header(None, alias="X-Internal-Token"),
) -> dict[str, str]:
    """Reinitialise les compteurs hit/miss du cache applicatif (PDS-46).

    Protege par un token optionnel (INTERNAL_API_TOKEN). Si le token est
    configure, il doit etre passe dans le header X-Internal-Token.
    Sans token configure, l'endpoint reste ouvert (dev local).
    """
    settings = get_settings()
    if settings.internal_api_token and (
        not x_internal_token or x_internal_token != settings.internal_api_token
    ):
        raise HTTPException(status_code=401, detail="Invalid or missing internal token")
    cache = SqlAlchemyQueryCacheRepository()
    cache.reset_stats()
    return {"message": "Cache stats reset"}

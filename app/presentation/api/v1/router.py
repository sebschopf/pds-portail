from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.application.use_cases.compare_datasets import (
    CompareDatasetsUseCase,
    InvalidCompareRequestError,
)
from app.application.use_cases.get_dataset_detail import GetDatasetDetailUseCase
from app.application.use_cases.get_health_status import GetHealthStatusUseCase
from app.application.use_cases.get_resource_detail import GetResourceDetailUseCase
from app.application.use_cases.search_datasets import SearchDatasetsUseCase
from app.infrastructure.persistence.cache_read_repository import SqlAlchemyCacheReadRepository
from app.infrastructure.persistence.search_repository import SqlAlchemySearchRepository
from app.presentation.api.v1.schemas import (
    CompareRequest,
    CompareResponse,
    DatasetDetailResponse,
    ResourceDetailResponse,
    SearchResponse,
)

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

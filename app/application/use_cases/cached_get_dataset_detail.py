"""Cas d'usage de detail dataset avec cache applicatif (PDS-46).

Wrappe GetDatasetDetailUseCase avec une couche de cache multi-niveaux :
- Niveau 1 : cache applicatif (query_cache SQLite)
- Niveau 2 : base de donnees (cache CKAN normalise)
"""

import json
import logging

from app.application.ports.query_cache_repository import QueryCacheRepositoryPort
from app.application.ports.search_repository import DatasetDetailRepositoryPort
from app.application.use_cases.get_dataset_detail import GetDatasetDetailUseCase
from app.domain.cache_invalidation import build_dataset_detail_cache_key
from app.presentation.api.v1.schemas import DatasetDetailResponse

logger = logging.getLogger(__name__)


class CachedGetDatasetDetailUseCase:
    """Detail dataset avec mise en cache applicatif transparente."""

    def __init__(
        self,
        repository: DatasetDetailRepositoryPort,
        cache: QueryCacheRepositoryPort,
        ttl_seconds: int = 86400,
    ) -> None:
        self._repository = repository
        self._cache = cache
        self._ttl_seconds = ttl_seconds
        self._inner = GetDatasetDetailUseCase(repository)

    def execute(self, dataset_id: str) -> DatasetDetailResponse | None:
        """Retourne le detail du dataset, depuis le cache si disponible.

        Args:
            dataset_id: ID du dataset (UUID CKAN)

        Returns:
            DatasetDetailResponse ou None si le dataset n'existe pas
        """
        from app.domain.cache_invalidation import CacheEndpointType

        cache_key = build_dataset_detail_cache_key(dataset_id)

        # Niveau 1 : cache applicatif
        cached = self._cache.get(cache_key, self._ttl_seconds)
        if cached is not None:
            try:
                data = json.loads(cached)
                return DatasetDetailResponse(**data)
            except (json.JSONDecodeError, TypeError):
                logger.warning("Cache JSON invalide pour dataset %s, bypass", dataset_id)

        # Niveau 2 : base de donnees
        detail = self._inner.execute(dataset_id)
        if detail is not None:
            # Serialiser et stocker dans le cache
            try:
                self._cache.set(
                    cache_key,
                    CacheEndpointType.DATASET_DETAIL,
                    detail.model_dump_json(),
                )
            except Exception:
                logger.exception("Echec ecriture cache pour dataset %s", dataset_id)

        return detail

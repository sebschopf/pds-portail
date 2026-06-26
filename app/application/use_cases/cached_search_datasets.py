"""Cas d'usage de recherche dataset avec cache applicatif (PDS-46).

Wrappe SearchDatasetsUseCase avec une couche de cache multi-niveaux.
"""

import json
import logging

from app.application.ports.query_cache_repository import QueryCacheRepositoryPort
from app.application.ports.search_repository import SearchRepositoryPort
from app.application.use_cases.search_datasets import SearchDatasetsUseCase
from app.domain.cache_invalidation import build_search_cache_key
from app.presentation.api.v1.schemas import SearchResponse

logger = logging.getLogger(__name__)


class CachedSearchDatasetsUseCase:
    """Recherche dataset avec mise en cache applicatif transparente."""

    def __init__(
        self,
        repository: SearchRepositoryPort,
        cache: QueryCacheRepositoryPort,
        ttl_seconds: int = 86400,
    ) -> None:
        self._repository = repository
        self._cache = cache
        self._ttl_seconds = ttl_seconds
        self._inner = SearchDatasetsUseCase(repository)

    def execute(
        self,
        query: str | None = None,
        offset: int = 0,
        limit: int = 20,
        org_filter: str | None = None,
        format_filter: str | None = None,
        tag_filter: str | None = None,
        sort: str = "modified_desc",
    ) -> SearchResponse:
        """Recherche les datasets, depuis le cache si disponible."""
        from app.domain.cache_invalidation import CacheEndpointType

        cache_key = build_search_cache_key(
            query=query,
            offset=offset,
            limit=limit,
            org_filter=org_filter,
            format_filter=format_filter,
            tag_filter=tag_filter,
            sort=sort,
        )

        cached = self._cache.get(cache_key, self._ttl_seconds)
        if cached is not None:
            try:
                data = json.loads(cached)
                return SearchResponse(**data)
            except (json.JSONDecodeError, TypeError):
                logger.warning("Cache JSON invalide pour search, bypass")

        result = self._inner.execute(
            query=query,
            offset=offset,
            limit=limit,
            org_filter=org_filter,
            format_filter=format_filter,
            tag_filter=tag_filter,
            sort=sort,
        )

        try:
            self._cache.set(
                cache_key,
                CacheEndpointType.SEARCH,
                result.model_dump_json(),
            )
        except Exception:
            logger.exception("Echec ecriture cache pour search")

        return result

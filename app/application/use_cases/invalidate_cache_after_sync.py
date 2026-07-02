"""Cas d'usage d'invalidation du cache applicatif apres sync CKAN (PDS-46).

Extrait et factorise la logique d'invalidation auparavant dupliquee
(ou absente) dans ``main.py`` et ``router.py``.

Applique les regles ADR-007, ADR-023 :
- SEARCH et FACETS sont toujours invalides globalement apres sync
- DATASET_DETAIL invalide par dataset specifique si IDs fournis
"""

import logging

from app.application.ports.query_cache_repository import QueryCacheRepositoryPort
from app.core.config import get_settings
from app.domain.cache_invalidation import CacheEndpointType

logger = logging.getLogger(__name__)


def invalidate_cache_after_sync(
    cache: QueryCacheRepositoryPort,
    synced_count: int,
    synced_dataset_ids: list[str] | None = None,
) -> None:
    """Invalide le cache applicatif apres un cycle de sync CKAN.

    Args:
        cache: Repository de cache applicatif
        synced_count: Nombre de datasets synchronises dans le cycle
        synced_dataset_ids: Liste optionnelle des IDs pour invalidation fine

    Les regles d'invalidation (ADR-007, ADR-023, PDS-109) :
    - SEARCH : invalide si >= 1 dataset sync (les resultats peuvent changer)
    - FACETS : invalide si >= 1 dataset sync (les compteurs peuvent changer)
    - EXPLORATION : invalide si >= 1 dataset sync (les ressources peuvent changer)
    - DATASET_DETAIL : invalide par dataset si synced_dataset_ids fournis
    """
    settings = get_settings()
    if not settings.query_cache_enabled:
        return
    if synced_count <= 0:
        return

    # Invalidation globale SEARCH + FACETS + EXPLORATION (PDS-109)
    search_deleted = cache.invalidate_by_endpoint_type(CacheEndpointType.SEARCH)
    facets_deleted = cache.invalidate_by_endpoint_type(CacheEndpointType.FACETS)
    exploration_deleted = cache.invalidate_by_endpoint_type(CacheEndpointType.EXPLORATION)
    logger.info(
        "Cache SEARCH+FACETS+EXPLORATION invalides apres sync: synced_datasets=%d, "
        "search_deleted=%d, facets_deleted=%d, exploration_deleted=%d",
        synced_count,
        search_deleted,
        facets_deleted,
        exploration_deleted,
    )

    # Invalidation fine DATASET_DETAIL
    if synced_dataset_ids:
        detail_deleted = 0
        for dataset_id in synced_dataset_ids:
            from app.domain.cache_invalidation import build_dataset_detail_cache_key

            key = build_dataset_detail_cache_key(dataset_id)
            if cache.invalidate_by_key(key):
                detail_deleted += 1
        if detail_deleted > 0:
            logger.info(
                "Cache DATASET_DETAIL invalide: %d entrées supprimées",
                detail_deleted,
            )

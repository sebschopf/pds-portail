"""Fakes partagés pour les tests unitaires des use cases (PDS-46)."""

from __future__ import annotations

from app.application.ports.query_cache_repository import CacheStats
from app.domain.cache_invalidation import CacheEndpointType


class FakeCacheRepository:
    """Fake in-memory pour QueryCacheRepositoryPort.

    Partagé entre test_cached_search_datasets et test_cached_get_dataset_detail.
    """

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.hits = 0
        self.misses = 0
        self.stale_count = 0
        self.invalidated: list[CacheEndpointType] = []

    def get(self, cache_key: str, ttl_seconds: int) -> str | None:  # noqa: ARG002
        if cache_key in self.store:
            self.hits += 1
            return self.store[cache_key]
        self.misses += 1
        return None

    def set(self, cache_key: str, endpoint_type: CacheEndpointType, response_json: str) -> None:
        del endpoint_type  # unused in fake
        self.store[cache_key] = response_json

    def invalidate_by_endpoint_type(self, endpoint_type: CacheEndpointType) -> int:
        self.invalidated.append(endpoint_type)
        count = sum(1 for k in list(self.store) if f":{endpoint_type.value}:" in k)
        self.store = {k: v for k, v in self.store.items() if f":{endpoint_type.value}:" not in k}
        return count

    def invalidate_by_key(self, cache_key: str) -> bool:
        if cache_key in self.store:
            del self.store[cache_key]
            return True
        return False

    def reset_stats(self) -> None:
        self.hits = 0
        self.misses = 0
        self.stale_count = 0

    def get_stats(self) -> CacheStats:
        return CacheStats(
            hits=self.hits,
            misses=self.misses,
            stale_entries=self.stale_count,
            total_entries=len(self.store),
        )

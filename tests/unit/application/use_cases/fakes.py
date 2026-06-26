"""Fakes partagés pour les tests unitaires des use cases (PDS-46, PDS-45)."""

from __future__ import annotations

from typing import Any, cast

from app.application.errors.ingestion import CkanRateLimitError, CkanTimeoutError
from app.application.ports.ckan_types import CkanPackageSearchResponse
from app.application.ports.query_cache_repository import CacheStats
from app.core.config import Settings
from app.domain.cache_invalidation import CacheEndpointType
from app.domain.ckan_normalized import NormalizedBatch

# ── FakeCacheRepository (PDS-46) ───────────────────────────────────────────


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


# ── Fakes synchronisation CKAN (PDS-45/PDS-52/PDS-53) ─────────────────────


class SyncCycleTestSettings(Settings):
    """Settings minimaux pour les tests du cycle de sync."""

    ckan_sync_batch_rows: int = 100
    ckan_sync_max_batches_per_run: int = 3
    ckan_sync_batch_delay_seconds: float = 0.0
    ckan_sync_interval_minutes: int = 60
    ckan_sync_bootstrap_if_empty: bool = False
    enable_ckan_sync: bool = True


class FakeSyncRepository:
    """Repository de test avec suivi d'appels pour les use cases de sync.

    Partagé entre test_run_sync_cycle et test_sync_ckan_batch_resilience.
    """

    def __init__(self) -> None:
        self._sync_states: dict[str, str] = {}
        self.was_called = False
        self.last_batch: NormalizedBatch | None = None
        self.upsert_calls: list[Any] = []
        self.metrics_calls: list[dict[str, int | str]] = []
        self.facets_rebuilt = False

    def upsert_normalized_batch(self, batch: Any) -> None:
        self.was_called = True
        self.last_batch = batch
        self.upsert_calls.append(batch)

    def get_sync_state(self, key: str) -> str | None:
        return self._sync_states.get(key)

    def set_sync_state(self, key: str, value: str) -> None:
        self._sync_states[key] = value

    def rebuild_facets(self) -> None:
        self.facets_rebuilt = True

    def add_sync_metrics(self, metrics: dict[str, int | str]) -> None:
        self.metrics_calls.append(metrics)

    def get_sync_state_updated_at(self, key: str) -> str | None:  # noqa: ARG002
        """Retourne None pour les tests (pas de tracking d'horodatage)."""
        return None


class FakeMinimalPayloadClient:
    """Client CKAN de test qui retourne des datasets synthetiques.

    Partagé entre test_run_sync_cycle et test_sync_ckan_batch_resilience.
    """

    def __init__(self, count: int = 100) -> None:
        self._count = count
        self.last_start: int | None = None
        self.last_modified_since: str | None = None

    def fetch_packages_batch(
        self, start: int, rows: int = 100, modified_since: str | None = None
    ) -> CkanPackageSearchResponse:
        self.last_start = start
        self.last_modified_since = modified_since
        _ = rows
        results: list[dict[str, Any]] = []
        for i in range(self._count):
            results.append(
                {
                    "id": f"ds-{start + i}",
                    "title": f"Dataset {start + i}",
                    "tags": [],
                    "organization": {"id": f"org-{i % 5}", "name": f"Org {i % 5}"},
                    "resources": [
                        {
                            "id": f"res-{start + i}",
                            "name": "CSV",
                            "format": "CSV",
                        }
                    ],
                }
            )
        return cast(
            CkanPackageSearchResponse,
            {"result": {"results": results}},
        )


class FakeTimeoutPayloadClient:
    """Client qui leve un timeout au premier appel (pour tester les metriques d'erreur)."""

    def fetch_packages_batch(
        self, start: int, rows: int = 100, modified_since: str | None = None
    ) -> CkanPackageSearchResponse:
        _ = (start, rows, modified_since)
        raise CkanTimeoutError("timeout test")


class FakeRateLimitPayloadClient:
    """Client qui leve un rate-limit au premier appel."""

    def fetch_packages_batch(
        self, start: int, rows: int = 100, modified_since: str | None = None
    ) -> CkanPackageSearchResponse:
        _ = (start, rows, modified_since)
        raise CkanRateLimitError("rate-limit")


class FakeFixedPayloadClient:
    """Client CKAN de test qui retourne un payload fixe predefini."""

    def __init__(self, payload: CkanPackageSearchResponse) -> None:
        self._payload = payload

    def fetch_packages_batch(
        self, start: int, rows: int = 100, modified_since: str | None = None
    ) -> CkanPackageSearchResponse:
        _ = (start, rows, modified_since)
        return self._payload

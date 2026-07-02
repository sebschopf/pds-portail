"""Fake implementations (mocks) centralisés pour tous les tests.

Ce module exporte tous les fakes (repositories, clients, etc.) réutilisables
pour les tests unitaires et d'intégration. Les fakes respectent les contrats
des ports sans appeler les vraies implémentations (BD, HTTP, filesystem, etc.).

Avantages:
- Tests rapides (pas d'I/O externe)
- Tests déterministes (pas de network/timing issues)
- Tests faciles à maintenir (un seul endroit pour changer un fake)
- Tests isolés (pas de dépendances externes)

Organisation:
- Fakes pour QueryCache (PDS-46)
- Fakes pour Synchronisation CKAN (PDS-45/PDS-52/PDS-53)
- Fakes pour Use Cases applicatifs
- Fakes pour Clients externes
"""

from __future__ import annotations

from typing import Any, cast

from app.application.errors.ingestion import CkanRateLimitError, CkanTimeoutError
from app.application.ports.ckan_types import CkanPackageSearchResponse
from app.application.ports.query_cache_repository import CacheStats
from app.core.config import Settings
from app.domain.cache_invalidation import CacheEndpointType
from app.domain.ckan_normalized import NormalizedBatch

# ──────────────────────────────────────────────────────────────────────────
# FAKES POUR QUERY CACHE (PDS-46)
# ──────────────────────────────────────────────────────────────────────────


class FakeCacheRepository:
    """Fake in-memory pour QueryCacheRepositoryPort.

    Simule un repository de cache applicatif qui stocke des réponses JSON
    indexées par clé, avec tracking de hits/misses/invalidations.

    Utilisé dans:
    - test_cached_search_datasets.py
    - test_cached_get_dataset_detail.py
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


# ──────────────────────────────────────────────────────────────────────────
# FAKES POUR SYNCHRONISATION CKAN (PDS-45/PDS-52/PDS-53)
# ──────────────────────────────────────────────────────────────────────────


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

    Simule un repository de synchronisation qui stocke les batches normalisés,
    l'état de sync, et les métriques. Utilisé pour vérifier que les use cases
    de sync appellent les bonnes méthodes avec les bons arguments.

    Utilisé dans:
    - test_run_sync_cycle.py
    - test_sync_ckan_batch_resilience.py
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
    """Client CKAN de test qui retourne des datasets synthétiques.

    Simule un client CKAN qui retourne des réponses batch avec datasets fictifs.
    Utilisé pour tester la logique de synchronisation sans faire de vrais appels HTTP.

    Utilisé dans:
    - test_run_sync_cycle.py
    - test_sync_ckan_batch_resilience.py
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
    """Client CKAN qui lève un timeout au premier appel.

    Utilisé pour tester la gestion des timeouts dans les use cases de sync.

    Utilisé dans:
    - test_sync_ckan_batch_resilience.py
    """

    def fetch_packages_batch(
        self, start: int, rows: int = 100, modified_since: str | None = None
    ) -> CkanPackageSearchResponse:
        _ = (start, rows, modified_since)
        raise CkanTimeoutError("timeout test")


class FakeRateLimitPayloadClient:
    """Client CKAN qui lève un rate-limit au premier appel.

    Utilisé pour tester la gestion des rate-limits dans les use cases de sync.

    Utilisé dans:
    - test_sync_ckan_batch_resilience.py
    """

    def fetch_packages_batch(
        self, start: int, rows: int = 100, modified_since: str | None = None
    ) -> CkanPackageSearchResponse:
        _ = (start, rows, modified_since)
        raise CkanRateLimitError("rate-limit")


class FakeFixedPayloadClient:
    """Client CKAN qui retourne un payload fixe prédéfini.

    Utilisé pour tester des scénarios spécifiques avec des données exactes.

    Utilisé dans:
    - test_run_sync_cycle.py
    """

    def __init__(self, payload: CkanPackageSearchResponse) -> None:
        self._payload = payload

    def fetch_packages_batch(
        self, start: int, rows: int = 100, modified_since: str | None = None
    ) -> CkanPackageSearchResponse:
        _ = (start, rows, modified_since)
        return self._payload


# ──────────────────────────────────────────────────────────────────────────
# FAKES POUR USE CASES (déplacés des fichiers de test)
# ──────────────────────────────────────────────────────────────────────────


class FakeDetailRepository:
    """Fake repository pour GetDatasetDetailUseCase.

    Simule un repository de détails dataset qui retourne une réponse fixe.
    Utilisé pour tester la logique de caching sur le use case sans BD réelle.

    Utilisé dans:
    - test_cached_get_dataset_detail.py

    Déplacé de: test_cached_get_dataset_detail.py::_FakeDetailRepository (local)
    """

    def __init__(self, detail: Any | None = None) -> None:
        self.detail = detail
        self.call_count = 0

    def get_by_id(self, dataset_id: str) -> Any:  # noqa: ARG002
        self.call_count += 1
        return self.detail


class FakeSearchRepository:
    """Fake repository pour CachedSearchDatasetsUseCase.

    Simule un repository de recherche qui retourne une réponse fixe.
    Utilisé pour tester la logique de caching sur le use case sans BD réelle.

    Utilisé dans:
    - test_cached_search_datasets.py

    Déplacé de: test_cached_search_datasets.py::_FakeSearchRepository (local)
    """

    def __init__(self, response: Any | None = None) -> None:
        self.response = response
        self.call_count = 0

    def search(self, query: str, **kwargs: Any) -> Any:  # noqa: ARG002
        self.call_count += 1
        return self.response


# ──────────────────────────────────────────────────────────────────────────
# FAKES POUR CLIENTS EXTERNES
# ──────────────────────────────────────────────────────────────────────────


class FakeCkanClient:
    """Client CKAN de test avec suivi des appels.

    Simule un client CKAN qui mémorise les appels fetch_packages_batch.
    Utilisé pour vérifier que la boucle de synchronisation appelle le client
    avec les bons paramètres (start, rows, offset).

    Utilisé dans:
    - test_sync_ckan_batch.py (integration test)

    Déplacé de: test_sync_ckan_batch.py::FakeCkanClient (local)
    """

    def __init__(self) -> None:
        self.calls: list[tuple[int, int]] = []

    def fetch_packages_batch(self, start: int, rows: int = 100) -> CkanPackageSearchResponse:
        self.calls.append((start, rows))
        return cast(
            CkanPackageSearchResponse,
            {"result": {"results": []}},
        )

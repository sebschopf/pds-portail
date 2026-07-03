"""Tests du use case RunSyncCycleUseCase (PDS-45) — cycle de sync CKAN avec metriques."""

from __future__ import annotations

from typing import Any, cast

from app.application.ports.ckan_types import CkanPackageSearchResponse
from app.application.use_cases.run_sync_cycle import RunSyncCycleUseCase

from .fakes import (
    FakeMinimalPayloadClient,
    FakeSyncRepository,
    FakeTimeoutPayloadClient,
    SyncCycleTestSettings,
)


def _int(value: int | str) -> int:
    """Helper type-safe pour extraire un int de ``dict[str, int | str]``."""
    if isinstance(value, int):
        return value
    return int(value)


class _DetectChangesSpy:
    def __init__(self) -> None:
        self.calls = 0

    def execute(self) -> dict[str, int]:
        self.calls += 1
        return {"inspected_datasets": 0, "changes_detected": 0}


# ── Tests bootstrap ────────────────────────────────────────────────────────


def test_cycle_bootstrap_stores_metrics() -> None:
    """Un cycle bootstrap persiste les metriques (synced_datasets, mode, duree)."""

    repository = FakeSyncRepository()
    client = FakeMinimalPayloadClient(count=100)
    settings = SyncCycleTestSettings(ckan_sync_max_batches_per_run=1)

    use_case = RunSyncCycleUseCase(client=client, repository=repository, settings=settings)
    result = use_case.execute()

    assert result["synced_datasets"] == 100
    assert _int(result["synced_organizations"]) > 0
    assert _int(result["synced_resources"]) > 0
    assert result["errors"] == 0
    assert result["mode"] == "bootstrap"
    assert _int(result["duration_ms"]) >= 0
    assert result["started_at"] is not None
    assert result["completed_at"] is not None

    # Les metriques sont persiste via add_sync_metrics
    assert len(repository.metrics_calls) == 1
    assert repository.metrics_calls[0]["mode"] == "bootstrap"
    assert repository.metrics_calls[0]["synced_datasets"] == 100


def test_cycle_bootstrap_advances_offset() -> None:
    """Apres un batch complet, l'offset est persiste et avance."""

    repository = FakeSyncRepository()
    client = FakeMinimalPayloadClient(count=100)
    settings = SyncCycleTestSettings(ckan_sync_max_batches_per_run=1)

    use_case = RunSyncCycleUseCase(client=client, repository=repository, settings=settings)
    use_case.execute()

    assert repository.get_sync_state("ckan_offset") == "100"


def test_cycle_bootstrap_detects_catalog_end() -> None:
    """Le second batch partiel declenche la reinitialisation offset + last_full_sync."""

    # Client a deux etapes : premier batch complet (100), second partiel (20)
    class _TwoStepClient:
        def __init__(self) -> None:
            self.calls = 0

        def fetch_packages_batch(
            self, start: int, rows: int = 100, modified_since: str | None = None
        ) -> CkanPackageSearchResponse:
            self.calls += 1
            _ = (start, rows, modified_since)
            count = 100 if self.calls == 1 else 20
            results: list[dict[str, Any]] = []
            for i in range(count):
                results.append(
                    {
                        "id": f"ds-{i}",
                        "title": f"Dataset {i}",
                        "tags": [],
                        "organization": {"id": "org-1", "name": "Org"},
                        "resources": [{"id": f"res-{i}", "name": "CSV", "format": "CSV"}],
                    }
                )
            return cast(
                CkanPackageSearchResponse,
                {"result": {"results": results}},
            )

    repository = FakeSyncRepository()
    client = _TwoStepClient()
    settings = SyncCycleTestSettings(ckan_sync_max_batches_per_run=2)

    use_case = RunSyncCycleUseCase(client=client, repository=repository, settings=settings)
    result = use_case.execute()

    # Le premier batch (100) + second (20 partiel) = 120 au total
    assert result["synced_datasets"] == 120
    # Offset reinitialise
    assert repository.get_sync_state("ckan_offset") == "0"
    # last_full_sync enregistre
    assert repository.get_sync_state("last_full_sync") is not None
    # Les facettes sont reconstruites
    assert repository.facets_rebuilt is True


def test_cycle_bootstrap_respects_max_batches() -> None:
    """Le cycle ne depasse pas ckan_sync_max_batches_per_run."""

    repository = FakeSyncRepository()
    client = FakeMinimalPayloadClient(count=100)
    settings = SyncCycleTestSettings(ckan_sync_max_batches_per_run=3)

    use_case = RunSyncCycleUseCase(client=client, repository=repository, settings=settings)
    result = use_case.execute()

    assert result["synced_datasets"] == 300  # 3 batches × 100
    assert repository.get_sync_state("ckan_offset") == "300"


def test_cycle_bootstrap_no_dataset_triggers_no_facets() -> None:
    """Un batch vide ne declenche pas la reconstruction des facettes."""

    repository = FakeSyncRepository()
    client = FakeMinimalPayloadClient(count=0)
    settings = SyncCycleTestSettings(ckan_sync_max_batches_per_run=1)

    use_case = RunSyncCycleUseCase(client=client, repository=repository, settings=settings)
    result = use_case.execute()

    assert result["synced_datasets"] == 0
    assert repository.facets_rebuilt is False
    # Metriques quand meme persiste
    assert len(repository.metrics_calls) == 1


# ── Tests differentiel (PDS-53) ─────────────────────────────────────────────


def test_cycle_differential_mode_stores_metrics() -> None:
    """En mode differentiel, les metriques sont persiste avec mode='differential'."""

    repository = FakeSyncRepository()
    repository.set_sync_state("last_full_sync", "2026-06-25T00:00:00+00:00")
    repository.set_sync_state("ckan_offset", "0")

    client = FakeMinimalPayloadClient(count=3)
    settings = SyncCycleTestSettings()

    use_case = RunSyncCycleUseCase(client=client, repository=repository, settings=settings)
    result = use_case.execute()

    assert result["mode"] == "differential"
    assert result["synced_datasets"] == 3
    assert len(repository.metrics_calls) == 1
    assert repository.metrics_calls[0]["mode"] == "differential"
    # last_full_sync mis a jour
    assert repository.get_sync_state("last_full_sync") is not None
    # Offset inchange (reste 0)
    assert repository.get_sync_state("ckan_offset") == "0"


def test_cycle_differential_handles_timeout_gracefully() -> None:
    """Un timeout en mode differentiel est capture et renvoie synced_datasets=0.

    Le CkanTimeoutError est absorbe dans SyncCkanBatchUseCase.execute() qui
    retourne un batch vide sans lever d'exception. Le cycle se termine
    proprement et persiste ses metriques.
    """

    repository = FakeSyncRepository()
    repository.set_sync_state("last_full_sync", "2026-06-25T00:00:00+00:00")
    repository.set_sync_state("ckan_offset", "0")

    client = FakeTimeoutPayloadClient()
    settings = SyncCycleTestSettings()

    use_case = RunSyncCycleUseCase(client=client, repository=repository, settings=settings)
    result = use_case.execute()

    assert result["mode"] == "differential"
    # Le timeout donne un batch vide → 0 datasets sync
    assert result["synced_datasets"] == 0
    # Les metriques sont quand meme persiste
    assert len(repository.metrics_calls) == 1


def test_cycle_bootstrap_with_partial_final_batch_resets_offset() -> None:
    """Un batch partiel en fin de bootstrap reinitialise offset et enregistre last_full_sync."""

    repository = FakeSyncRepository()
    repository.set_sync_state("ckan_offset", "0")

    # 1 batch complet puis 1 partiel
    class _TwoStepClient:
        def __init__(self) -> None:
            self.calls = 0

        def fetch_packages_batch(
            self, start: int, rows: int = 100, modified_since: str | None = None
        ) -> CkanPackageSearchResponse:
            self.calls += 1
            _ = (start, rows, modified_since)
            count = 100 if self.calls == 1 else 30
            results: list[dict[str, Any]] = []
            for i in range(count):
                results.append(
                    {
                        "id": f"ds-{i}",
                        "title": f"Dataset {i}",
                        "tags": [],
                        "organization": {"id": "org-1", "name": "Org"},
                        "resources": [{"id": f"res-{i}", "name": "CSV", "format": "CSV"}],
                    }
                )
            return cast(
                CkanPackageSearchResponse,
                {"result": {"results": results}},
            )

    client = _TwoStepClient()
    settings = SyncCycleTestSettings(ckan_sync_max_batches_per_run=3)

    use_case = RunSyncCycleUseCase(client=client, repository=repository, settings=settings)
    result = use_case.execute()

    assert result["synced_datasets"] == 130
    assert repository.get_sync_state("ckan_offset") == "0"
    assert repository.get_sync_state("last_full_sync") is not None


# ── Test metriques sur batchs multiples ────────────────────────────────────


def test_metrics_aggregate_across_multiple_batches() -> None:
    """Les metriques totalisent synced_datasets sur tous les batchs du cycle."""

    repository = FakeSyncRepository()
    client = FakeMinimalPayloadClient(count=100)
    settings = SyncCycleTestSettings(ckan_sync_max_batches_per_run=5)

    use_case = RunSyncCycleUseCase(client=client, repository=repository, settings=settings)
    result = use_case.execute()

    assert result["synced_datasets"] == 500
    assert result["errors"] == 0
    assert len(repository.metrics_calls) == 1
    assert repository.metrics_calls[0]["synced_datasets"] == 500


def test_cycle_executes_detect_changes_once() -> None:
    """Le cycle complet appelle la détection des changements en fin d'execution."""

    repository = FakeSyncRepository()
    client = FakeMinimalPayloadClient(count=100)
    settings = SyncCycleTestSettings(ckan_sync_max_batches_per_run=1)
    detect_changes = _DetectChangesSpy()

    use_case = RunSyncCycleUseCase(
        client=client,
        repository=repository,
        settings=settings,
        detect_changes_use_case=detect_changes,
    )

    use_case.execute()

    assert detect_changes.calls == 1

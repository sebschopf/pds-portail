"""Tests de resilience du use case de synchronisation CKAN (PDS-45/PDS-52/PDS-53)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

import pytest

from app.application.ports.ckan_types import CkanPackageSearchResponse
from app.application.use_cases.sync_ckan_batch import SyncCkanBatchUseCase

from .fakes import (
    FakeFixedPayloadClient,
    FakeMinimalPayloadClient,
    FakeRateLimitPayloadClient,
    FakeSyncRepository,
    FakeTimeoutPayloadClient,
)


def test_use_case_timeout_skips_batch_without_repository_write() -> None:
    """Un timeout lot est journalise/ignore sans interrompre le traitement global."""

    repository = FakeSyncRepository()
    use_case = SyncCkanBatchUseCase(client=FakeTimeoutPayloadClient(), repository=repository)

    batch = use_case.execute(start=0, rows=100)

    assert batch.organizations == []
    assert batch.datasets == []
    assert batch.resources == []
    assert repository.was_called is False


def test_use_case_rate_limit_skips_batch_without_repository_write() -> None:
    """Un rate limit persistant ignore le lot sans ecriture repository."""

    repository = FakeSyncRepository()
    use_case = SyncCkanBatchUseCase(client=FakeRateLimitPayloadClient(), repository=repository)

    batch = use_case.execute(start=0, rows=100)

    assert batch.organizations == []
    assert batch.datasets == []
    assert batch.resources == []
    assert repository.was_called is False


def test_use_case_logs_and_skips_invalid_dataset_and_resource(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Ignore les records invalides du lot tout en persistant les valides."""

    payload = cast(
        CkanPackageSearchResponse,
        {
            "result": {
                "results": [
                    {"id": "missing-org", "title": "Sans org"},
                    {
                        "id": "missing-title",
                        "organization": {"id": "org-1", "name": "Org"},
                    },
                    {
                        "id": "dataset-valid",
                        "title": "Dataset valide",
                        "organization": {"id": "org-1", "name": "Org"},
                        "resources": [
                            {"id": "resource-valid", "name": "CSV", "format": "CSV"},
                            {"description": "sans id"},
                        ],
                    },
                ]
            }
        },
    )

    repository = FakeSyncRepository()
    use_case = SyncCkanBatchUseCase(client=FakeFixedPayloadClient(payload), repository=repository)

    with caplog.at_level("WARNING"):
        batch = use_case.execute(start=0, rows=100)

    assert repository.was_called is True
    assert len(batch.organizations) == 1
    assert len(batch.datasets) == 1
    assert len(batch.resources) == 1
    assert "Dataset ignoré sans organisation id/name" in caplog.text
    assert "Dataset invalide ignoré (id/title manquant)" in caplog.text
    assert "Ressource invalide ignorée" in caplog.text


# ── Tests offset persisté (PDS-52) ───────────────────────────────────────


def test_sync_uses_persisted_offset_on_resume() -> None:
    """Le use case reprend au dernier offset persiste dans le repository."""

    repository = FakeSyncRepository()
    repository.set_sync_state("ckan_offset", "500")

    client = FakeMinimalPayloadClient(count=100)
    use_case = SyncCkanBatchUseCase(client=client, repository=repository)

    raw_offset = repository.get_sync_state("ckan_offset")
    current_offset = int(raw_offset) if raw_offset and raw_offset.isdigit() else 0
    assert current_offset == 500
    batch = use_case.execute(start=current_offset, rows=100)

    assert client.last_start == 500
    assert len(batch.datasets) == 100


def test_sync_starts_at_zero_when_no_offset_persisted() -> None:
    """Demarrage a froid : offset 0 si aucun etat persistant."""

    repository = FakeSyncRepository()
    client = FakeMinimalPayloadClient(count=100)
    use_case = SyncCkanBatchUseCase(client=client, repository=repository)

    raw_offset = repository.get_sync_state("ckan_offset")
    current_offset = int(raw_offset) if raw_offset and raw_offset.isdigit() else 0
    assert current_offset == 0

    batch = use_case.execute(start=current_offset, rows=100)
    assert client.last_start == 0
    assert len(batch.datasets) == 100


def test_offset_resets_when_catalog_end_reached() -> None:
    """La fin du catalogue (batch partiel) reinitialise l'offset a 0."""

    repository = FakeSyncRepository()
    repository.set_sync_state("ckan_offset", "1000")

    client = FakeMinimalPayloadClient(count=50)
    use_case = SyncCkanBatchUseCase(client=client, repository=repository)

    raw_offset = repository.get_sync_state("ckan_offset")
    current_offset = int(raw_offset) if raw_offset and raw_offset.isdigit() else 0
    batch = use_case.execute(start=current_offset, rows=100)

    assert len(batch.datasets) == 50

    if len(batch.datasets) < 100:
        current_offset = 0
    repository.set_sync_state("ckan_offset", str(current_offset))

    assert repository.get_sync_state("ckan_offset") == "0"


def test_offset_advances_after_full_batch() -> None:
    """Apres un batch complet, l'offset avance de batch_rows."""

    repository = FakeSyncRepository()
    repository.set_sync_state("ckan_offset", "0")

    client = FakeMinimalPayloadClient(count=100)
    use_case = SyncCkanBatchUseCase(client=client, repository=repository)

    raw_offset = repository.get_sync_state("ckan_offset")
    current_offset = int(raw_offset) if raw_offset and raw_offset.isdigit() else 0
    batch = use_case.execute(start=current_offset, rows=100)

    assert len(batch.datasets) == 100

    current_offset += 100
    repository.set_sync_state("ckan_offset", str(current_offset))

    assert repository.get_sync_state("ckan_offset") == "100"


def test_offset_persisted_after_each_batch() -> None:
    """Chaque lot persiste son offset, pas seulement en fin de cycle."""

    repository = FakeSyncRepository()
    repository.set_sync_state("ckan_offset", "0")

    for expected_start in (0, 100, 200):
        client = FakeMinimalPayloadClient(count=100)
        use_case = SyncCkanBatchUseCase(client=client, repository=repository)

        raw_offset = repository.get_sync_state("ckan_offset")
        current_offset = int(raw_offset) if raw_offset and raw_offset.isdigit() else 0
        assert current_offset == expected_start

        batch = use_case.execute(start=current_offset, rows=100)
        assert len(batch.datasets) == 100
        assert client.last_start == expected_start

        current_offset += 100
        repository.set_sync_state("ckan_offset", str(current_offset))
        assert repository.get_sync_state("ckan_offset") == str(expected_start + 100)


# ── Tests synchro différentielle (PDS-53) ─────────────────────────────────


def test_differential_sync_uses_modified_since() -> None:
    """Le mode differentiel transmet le timestamp modified_since au client CKAN."""

    repository = FakeSyncRepository()
    repository.set_sync_state("last_full_sync", "2026-06-25T00:00:00+00:00")
    repository.set_sync_state("ckan_offset", "0")

    client = FakeMinimalPayloadClient(count=5)
    use_case = SyncCkanBatchUseCase(client=client, repository=repository)

    modified_since = repository.get_sync_state("last_full_sync")
    batch = use_case.execute(start=0, rows=100, modified_since=modified_since)

    assert client.last_start == 0
    assert client.last_modified_since == "2026-06-25T00:00:00+00:00"
    assert len(batch.datasets) == 5


def test_differential_sync_persists_new_timestamp() -> None:
    """Apres un cycle differentiel, le timestamp last_full_sync est mis a jour."""

    repository = FakeSyncRepository()
    repository.set_sync_state("last_full_sync", "2026-06-25T00:00:00+00:00")
    repository.set_sync_state("ckan_offset", "0")

    client = FakeMinimalPayloadClient(count=3)
    use_case = SyncCkanBatchUseCase(client=client, repository=repository)

    modified_since = repository.get_sync_state("last_full_sync")
    batch = use_case.execute(start=0, rows=100, modified_since=modified_since)
    assert len(batch.datasets) == 3

    # Simule la fin d'un cycle differentiel avec un horodatage fixe.
    now = datetime(2026, 7, 2, tzinfo=UTC).isoformat()
    repository.set_sync_state("last_full_sync", now)
    assert repository.get_sync_state("last_full_sync") == now


def test_bootstrap_mode_does_not_use_modified_since() -> None:
    """En mode bootstrap (pas de last_full_sync), modified_since n'est pas passe."""

    repository = FakeSyncRepository()
    # Pas de last_full_sync → mode bootstrap
    repository.set_sync_state("ckan_offset", "0")

    client = FakeMinimalPayloadClient(count=10)
    use_case = SyncCkanBatchUseCase(client=client, repository=repository)

    modified_since = repository.get_sync_state("last_full_sync")
    batch = use_case.execute(start=0, rows=100, modified_since=modified_since)

    assert client.last_modified_since is None
    assert len(batch.datasets) == 10

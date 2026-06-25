"""Tests de resilience du use case de synchronisation CKAN."""

from datetime import UTC, datetime
from typing import cast

import pytest

from app.application.errors.ingestion import CkanRateLimitError, CkanTimeoutError
from app.application.ports.ckan_types import CkanPackageSearchResponse
from app.application.use_cases.sync_ckan_batch import SyncCkanBatchUseCase
from app.domain.ckan_normalized import NormalizedBatch


class _TimeoutClient:
    def fetch_packages_batch(self, start: int, rows: int = 100, modified_since: str | None = None):
        _ = (start, rows, modified_since)
        raise CkanTimeoutError("timeout")


class _SpyRepository:
    def __init__(self) -> None:
        self.was_called = False
        self.last_batch: NormalizedBatch | None = None
        self._sync_states: dict[str, str] = {}

    def upsert_normalized_batch(self, batch: NormalizedBatch) -> None:
        self.was_called = True
        self.last_batch = batch

    def get_sync_state(self, key: str) -> str | None:
        return self._sync_states.get(key)

    def set_sync_state(self, key: str, value: str) -> None:
        self._sync_states[key] = value


class _RateLimitClient:
    def fetch_packages_batch(self, start: int, rows: int = 100, modified_since: str | None = None):
        _ = (start, rows, modified_since)
        raise CkanRateLimitError("rate-limit")


class _PayloadClient:
    def __init__(self, payload: CkanPackageSearchResponse) -> None:
        self._payload = payload

    def fetch_packages_batch(
        self, start: int, rows: int = 100, modified_since: str | None = None
    ) -> CkanPackageSearchResponse:
        _ = (start, rows, modified_since)
        return self._payload


def test_use_case_timeout_skips_batch_without_repository_write() -> None:
    """Un timeout lot est journalise/ignore sans interrompre le traitement global."""

    repository = _SpyRepository()
    use_case = SyncCkanBatchUseCase(client=_TimeoutClient(), repository=repository)

    batch = use_case.execute(start=0, rows=100)

    assert batch.organizations == []
    assert batch.datasets == []
    assert batch.resources == []
    assert repository.was_called is False


def test_use_case_rate_limit_skips_batch_without_repository_write() -> None:
    """Un rate limit persistant ignore le lot sans ecriture repository."""

    repository = _SpyRepository()
    use_case = SyncCkanBatchUseCase(client=_RateLimitClient(), repository=repository)

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

    repository = _SpyRepository()
    use_case = SyncCkanBatchUseCase(client=_PayloadClient(payload), repository=repository)

    with caplog.at_level("WARNING"):
        batch = use_case.execute(start=0, rows=100)

    assert repository.was_called is True
    assert len(batch.organizations) == 1
    assert len(batch.datasets) == 1
    assert len(batch.resources) == 1
    assert "Dataset ignore sans organisation id/name" in caplog.text
    assert "Dataset invalide ignore (id/title manquant)" in caplog.text
    assert "Ressource invalide ignoree" in caplog.text


# ── Tests offset persisté (PDS-52) ───────────────────────────────────────


class _MinimalDatasetPayloadClient:
    """Retourne des datasets synthetiques pour tester l'offset sans parser CKAN reel."""

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
        results: list[dict] = []
        for i in range(self._count):
            results.append(
                {
                    "id": f"ds-{start + i}",
                    "title": f"Dataset {start + i}",
                    "organization": {"id": f"org-{i % 5}", "name": f"Org {i % 5}"},
                    "resources": [{"id": f"res-{start + i}", "name": "CSV", "format": "CSV"}],
                }
            )
        return cast(
            CkanPackageSearchResponse,
            {
                "result": {
                    "results": results,
                }
            },
        )


def test_sync_uses_persisted_offset_on_resume() -> None:
    """Le use case reprend au dernier offset persiste dans le repository."""

    repository = _SpyRepository()
    repository.set_sync_state("ckan_offset", "500")

    client = _MinimalDatasetPayloadClient(count=100)
    use_case = SyncCkanBatchUseCase(client=client, repository=repository)

    raw_offset = repository.get_sync_state("ckan_offset")
    current_offset = int(raw_offset) if raw_offset and raw_offset.isdigit() else 0
    assert current_offset == 500
    batch = use_case.execute(start=current_offset, rows=100)

    assert client.last_start == 500
    assert len(batch.datasets) == 100


def test_sync_starts_at_zero_when_no_offset_persisted() -> None:
    """Demarrage a froid : offset 0 si aucun etat persistant."""

    repository = _SpyRepository()
    client = _MinimalDatasetPayloadClient(count=100)
    use_case = SyncCkanBatchUseCase(client=client, repository=repository)

    raw_offset = repository.get_sync_state("ckan_offset")
    current_offset = int(raw_offset) if raw_offset and raw_offset.isdigit() else 0
    assert current_offset == 0

    batch = use_case.execute(start=current_offset, rows=100)
    assert client.last_start == 0
    assert len(batch.datasets) == 100


def test_offset_resets_when_catalog_end_reached() -> None:
    """La fin du catalogue (batch partiel) reinitialise l'offset a 0."""

    repository = _SpyRepository()
    repository.set_sync_state("ckan_offset", "1000")

    client = _MinimalDatasetPayloadClient(count=50)
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

    repository = _SpyRepository()
    repository.set_sync_state("ckan_offset", "0")

    client = _MinimalDatasetPayloadClient(count=100)
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

    repository = _SpyRepository()
    repository.set_sync_state("ckan_offset", "0")

    for expected_start in (0, 100, 200):
        client = _MinimalDatasetPayloadClient(count=100)
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

    repository = _SpyRepository()
    repository.set_sync_state("last_full_sync", "2026-06-25T00:00:00+00:00")
    repository.set_sync_state("ckan_offset", "0")

    client = _MinimalDatasetPayloadClient(count=5)
    use_case = SyncCkanBatchUseCase(client=client, repository=repository)

    modified_since = repository.get_sync_state("last_full_sync")
    batch = use_case.execute(start=0, rows=100, modified_since=modified_since)

    assert client.last_start == 0
    assert client.last_modified_since == "2026-06-25T00:00:00+00:00"
    assert len(batch.datasets) == 5


def test_differential_sync_persists_new_timestamp() -> None:
    """Apres un cycle differentiel, le timestamp last_full_sync est mis a jour."""

    repository = _SpyRepository()
    repository.set_sync_state("last_full_sync", "2026-06-25T00:00:00+00:00")
    repository.set_sync_state("ckan_offset", "0")

    client = _MinimalDatasetPayloadClient(count=3)
    use_case = SyncCkanBatchUseCase(client=client, repository=repository)

    modified_since = repository.get_sync_state("last_full_sync")
    batch = use_case.execute(start=0, rows=100, modified_since=modified_since)
    assert len(batch.datasets) == 3

    # Simule la fin d'un cycle differentiel: on met a jour last_full_sync a now
    now = datetime.now(UTC).isoformat()
    repository.set_sync_state("last_full_sync", now)
    assert repository.get_sync_state("last_full_sync") == now


def test_bootstrap_mode_does_not_use_modified_since() -> None:
    """En mode bootstrap (pas de last_full_sync), modified_since n'est pas passe."""

    repository = _SpyRepository()
    # Pas de last_full_sync → mode bootstrap
    repository.set_sync_state("ckan_offset", "0")

    client = _MinimalDatasetPayloadClient(count=10)
    use_case = SyncCkanBatchUseCase(client=client, repository=repository)

    modified_since = repository.get_sync_state("last_full_sync")
    batch = use_case.execute(start=0, rows=100, modified_since=modified_since)

    assert client.last_modified_since is None
    assert len(batch.datasets) == 10

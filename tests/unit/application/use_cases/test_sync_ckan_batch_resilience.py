"""Tests de resilience du use case de synchronisation CKAN."""

from typing import cast

import pytest

from app.application.errors.ingestion import CkanRateLimitError, CkanTimeoutError
from app.application.ports.ckan_types import CkanPackageSearchResponse
from app.application.use_cases.sync_ckan_batch import SyncCkanBatchUseCase
from app.domain.ckan_normalized import NormalizedBatch


class _TimeoutClient:
    def fetch_packages_batch(self, start: int, rows: int = 100):
        _ = (start, rows)
        raise CkanTimeoutError("timeout")


class _SpyRepository:
    def __init__(self) -> None:
        self.was_called = False
        self.last_batch: NormalizedBatch | None = None

    def upsert_normalized_batch(self, batch: NormalizedBatch) -> None:
        self.was_called = True
        self.last_batch = batch


class _RateLimitClient:
    def fetch_packages_batch(self, start: int, rows: int = 100):
        _ = (start, rows)
        raise CkanRateLimitError("rate-limit")


class _PayloadClient:
    def __init__(self, payload: CkanPackageSearchResponse) -> None:
        self._payload = payload

    def fetch_packages_batch(self, start: int, rows: int = 100) -> CkanPackageSearchResponse:
        _ = (start, rows)
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

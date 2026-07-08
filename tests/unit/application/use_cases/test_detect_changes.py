"""Tests unitaires du use case DetectChangesUseCase (PDS-87)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import httpx
import pytest

from app.application.ports.cache_read_repository import CacheReadRepositoryPort
from app.application.ports.changelog_repository import ChangeLogEntry, ChangeLogRepositoryPort
from app.application.ports.watcher_repository import WatchedDataset, Watcher, WatcherRepositoryPort
from app.application.use_cases.detect_changes import DetectChangesUseCase
from app.presentation.api.v1.schemas import (
    DatasetDetailResponse,
    DatasetStructure,
    ResourceResponse,
)


@dataclass
class _FakeCacheRepository:
    datasets: dict[str, DatasetDetailResponse]

    def get_dataset(self, dataset_id: str) -> DatasetDetailResponse | None:
        return self.datasets.get(dataset_id)


class _FakeWatcherRepository:
    def __init__(self, watched_datasets: list[WatchedDataset]) -> None:
        self._watched_datasets = watched_datasets
        self.updated_last_known: list[tuple[str, str, str | None, int | None, float | None]] = []

    def list_watched_datasets(self) -> list[WatchedDataset]:
        return self._watched_datasets

    def find_by_polar_subscription_id(self, polar_subscription_id: str) -> Watcher | None:
        _ = polar_subscription_id
        return None

    def update_last_known(
        self,
        watcher_id: str,
        dataset_id: str,
        metadata_modified: str | None,
        resource_count: int | None,
        quality_score: float | None,
    ) -> None:
        self.updated_last_known.append(
            (watcher_id, dataset_id, metadata_modified, resource_count, quality_score)
        )

    def find_last_alert_sent_at(self, watcher_id: str, dataset_id: str) -> str | None:
        _ = (watcher_id, dataset_id)
        return None

    def mark_alert_sent(self, watcher_id: str, dataset_id: str, sent_at: str) -> None:
        _ = (watcher_id, dataset_id, sent_at)


class _FakeChangeLogRepository:
    def __init__(self) -> None:
        self.entries: list[ChangeLogEntry] = []

    def insert(
        self,
        dataset_id: str,
        change_type: str,
        previous_value: str | None,
        new_value: str | None,
        detected_at: str,
    ) -> ChangeLogEntry:
        entry = ChangeLogEntry(
            id=f"entry-{len(self.entries) + 1}",
            dataset_id=dataset_id,
            change_type=change_type,
            previous_value=previous_value,
            new_value=new_value,
            detected_at=detected_at,
            notified_at=None,
        )
        self.entries.append(entry)
        return entry


@pytest.fixture(autouse=True)
def _mock_successful_head(
    monkeypatch: pytest.MonkeyPatch,
) -> None:  # pyright: ignore[reportUnusedFunction]
    """Neutralise les HEAD HTTP en scénario nominal pour garder les tests déterministes."""

    def _fake_head(*args: Any, **kwargs: Any) -> httpx.Response:
        _ = (args, kwargs)
        return httpx.Response(
            status_code=200,
            request=httpx.Request("HEAD", "https://example.com/resource.csv"),
        )

    monkeypatch.setattr("app.application.use_cases.detect_changes.httpx.head", _fake_head)


_ = _mock_successful_head


@pytest.fixture
def watched_dataset() -> WatchedDataset:
    return WatchedDataset(
        id="wd-1",
        watcher_id="watcher-1",
        dataset_id="dataset-1",
        last_known_metadata_modified="2026-06-01T00:00:00+00:00",
        last_known_resource_count=1,
        last_known_quality_score=60.0,
        created_at="2026-06-01T00:00:00+00:00",
    )


@pytest.fixture
def dataset_detail() -> DatasetDetailResponse:
    return DatasetDetailResponse(
        id="dataset-1",
        title="Dataset 1",
        description="Description mise a jour",
        org_id="org-1",
        org_name="Org 1",
        license=None,
        author=None,
        created="2026-06-01T00:00:00+00:00",
        modified="2026-07-01T00:00:00+00:00",
        quality_score=0,
        completeness=0,
        freshness_days=0,
        dataset_structure=DatasetStructure(
            fields=[],
            formats=["CSV"],
            update_frequency=None,
            last_updated="2026-07-01T00:00:00+00:00",
        ),
        access_modes=[],
        resources=[
            ResourceResponse(
                id="res-1",
                name="Ressource 1",
                format="CSV",
                url="https://example.com/resource.csv",
            )
        ],
        tags=["open-data"],
        ckan_url=None,
    )


def _build_use_case(
    watched_datasets: list[WatchedDataset],
    dataset_detail: DatasetDetailResponse,
) -> tuple[DetectChangesUseCase, _FakeWatcherRepository, _FakeChangeLogRepository]:
    watcher_repository = _FakeWatcherRepository(watched_datasets)
    changelog_repository = _FakeChangeLogRepository()
    cache_repository = _FakeCacheRepository(datasets={dataset_detail.id: dataset_detail})

    use_case = DetectChangesUseCase(
        watcher_repository=cast(WatcherRepositoryPort, watcher_repository),
        changelog_repository=cast(ChangeLogRepositoryPort, changelog_repository),
        cache_repository=cast(CacheReadRepositoryPort, cache_repository),
    )
    return use_case, watcher_repository, changelog_repository


def test_detect_changes_metadata_updated_logs_change(
    watched_dataset: WatchedDataset,
    dataset_detail: DatasetDetailResponse,
) -> None:
    """La modification de metadata_updated est journalisee."""

    use_case, watcher_repository, changelog_repository = _build_use_case(
        [watched_dataset], dataset_detail
    )

    result = use_case.execute()

    assert result["inspected_datasets"] == 1
    assert result["changes_detected"] == 1
    assert changelog_repository.entries[0].change_type == "metadata_updated"
    assert watcher_repository.updated_last_known[0][2] == dataset_detail.modified


def test_detect_changes_resource_added_logs_change(
    watched_dataset: WatchedDataset,
    dataset_detail: DatasetDetailResponse,
) -> None:
    """L'ajout de ressource est journalise."""

    dataset_detail = dataset_detail.model_copy(
        update={"modified": watched_dataset.last_known_metadata_modified}
    )
    dataset_detail = dataset_detail.model_copy(
        update={
            "resources": [
                *dataset_detail.resources,
                ResourceResponse(
                    id="res-2",
                    name="Ressource 2",
                    format="CSV",
                    url="https://example.com/resource-2.csv",
                ),
            ]
        }
    )
    use_case, _, changelog_repository = _build_use_case([watched_dataset], dataset_detail)

    result = use_case.execute()

    assert result["changes_detected"] == 1
    assert any(entry.change_type == "resource_added" for entry in changelog_repository.entries)


def test_detect_changes_resource_removed_logs_change(
    watched_dataset: WatchedDataset,
    dataset_detail: DatasetDetailResponse,
) -> None:
    """La suppression de ressource est journalisee."""

    dataset_detail = dataset_detail.model_copy(
        update={"modified": watched_dataset.last_known_metadata_modified}
    )
    watched_dataset = watched_dataset._replace(last_known_resource_count=3)
    use_case, _, changelog_repository = _build_use_case([watched_dataset], dataset_detail)

    result = use_case.execute()

    assert result["changes_detected"] == 1
    assert any(entry.change_type == "resource_removed" for entry in changelog_repository.entries)


def test_detect_changes_quality_degraded_logs_change(
    watched_dataset: WatchedDataset,
    dataset_detail: DatasetDetailResponse,
) -> None:
    """Une degradation de qualite au-dela du seuil est journalisee."""

    degraded_detail = dataset_detail.model_copy(update={"modified": "2020-01-01T00:00:00+00:00"})
    watched_dataset = watched_dataset._replace(
        last_known_metadata_modified="2020-01-01T00:00:00+00:00",
        last_known_quality_score=80.0,
    )
    use_case, _, changelog_repository = _build_use_case([watched_dataset], degraded_detail)

    result = use_case.execute()

    assert result["changes_detected"] == 1
    assert any(entry.change_type == "quality_degraded" for entry in changelog_repository.entries)


def test_detect_changes_link_broken_logs_change(
    watched_dataset: WatchedDataset,
    dataset_detail: DatasetDetailResponse,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Un lien de ressource cassé est journalisé."""

    dataset_detail = dataset_detail.model_copy(
        update={"modified": watched_dataset.last_known_metadata_modified}
    )
    use_case, _, changelog_repository = _build_use_case([watched_dataset], dataset_detail)

    def _fake_head(*args: Any, **kwargs: Any) -> httpx.Response:
        _ = (args, kwargs)
        return httpx.Response(
            status_code=500,
            request=httpx.Request("HEAD", "https://example.com/resource.csv"),
        )

    monkeypatch.setattr("app.application.use_cases.detect_changes.httpx.head", _fake_head)

    result = use_case.execute()

    assert result["changes_detected"] == 1
    assert any(entry.change_type == "link_broken" for entry in changelog_repository.entries)


def test_detect_changes_no_change_updates_last_known_without_log(
    watched_dataset: WatchedDataset,
    dataset_detail: DatasetDetailResponse,
) -> None:
    """Sans changement, les dernières valeurs connues sont mises à jour sans log."""

    unchanged_detail = dataset_detail.model_copy(
        update={
            "modified": "2026-07-01T00:00:00+00:00",
            "resources": [
                ResourceResponse(
                    id="res-1",
                    name="Ressource 1",
                    format="CSV",
                    url="https://example.com/resource.csv",
                )
            ],
        }
    )
    watched_dataset = watched_dataset._replace(
        last_known_metadata_modified="2026-07-01T00:00:00+00:00",
        last_known_quality_score=80.0,
    )
    use_case, watcher_repository, changelog_repository = _build_use_case(
        [watched_dataset], unchanged_detail
    )

    result = use_case.execute()

    assert result["changes_detected"] == 0
    assert changelog_repository.entries == []
    assert (
        watcher_repository.updated_last_known[0][2] == watched_dataset.last_known_metadata_modified
    )

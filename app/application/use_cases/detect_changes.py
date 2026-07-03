"""Cas d'usage de détection des changements d'état sur les datasets surveillés."""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime

import httpx

from app.application.ports.cache_read_repository import CacheReadRepositoryPort
from app.application.ports.changelog_repository import ChangeLogRepositoryPort
from app.application.ports.watcher_repository import WatchedDataset, WatcherRepositoryPort
from app.domain.quality_indicators import DatasetIndicatorInput, compute_indicators
from app.presentation.api.v1.schemas import DatasetDetailResponse

logger = logging.getLogger(__name__)

_RESOURCE_HEAD_TIMEOUT_SECONDS = 5.0
_QUALITY_DROP_THRESHOLD = 5


class DetectChangesUseCase:
    """Compare l'état courant des datasets avec le dernier état connu."""

    def __init__(
        self,
        watcher_repository: WatcherRepositoryPort,
        changelog_repository: ChangeLogRepositoryPort,
        cache_repository: CacheReadRepositoryPort,
    ) -> None:
        self._watcher_repository = watcher_repository
        self._changelog_repository = changelog_repository
        self._cache_repository = cache_repository

    def execute(self) -> dict[str, int]:
        """Détecte les changements et persiste le journal associé."""

        watched_datasets = self._watcher_repository.list_watched_datasets()
        grouped_datasets = self._group_by_dataset_id(watched_datasets)

        inspected_datasets = 0
        changes_detected = 0

        for dataset_id, watched_items in grouped_datasets.items():
            # Contrat de lecture explicite: SPEC-009 §3.1 + ADR-030.
            # Tout nouvel adapter raccordé à cette détection doit exposer get_dataset(dataset_id).
            dataset = self._cache_repository.get_dataset(dataset_id)
            if dataset is None:
                logger.info("Dataset surveille introuvable dans le cache: %s", dataset_id)
                continue

            inspected_datasets += 1
            current_metadata_modified = dataset.modified
            current_resource_count = len(dataset.resources)
            current_quality_score = self._compute_quality_score(dataset)

            changes_detected += self._log_metadata_changes(
                watched_items,
                dataset_id,
                current_metadata_modified,
            )
            changes_detected += self._log_resource_count_changes(
                watched_items,
                dataset_id,
                current_resource_count,
            )
            changes_detected += self._log_quality_changes(
                watched_items,
                dataset_id,
                current_quality_score,
            )
            changes_detected += self._log_link_changes(dataset_id, dataset.resources)

            for watched_item in watched_items:
                self._watcher_repository.update_last_known(
                    watcher_id=watched_item.watcher_id,
                    dataset_id=dataset_id,
                    metadata_modified=current_metadata_modified,
                    resource_count=current_resource_count,
                    quality_score=float(current_quality_score),
                )

        return {
            "inspected_datasets": inspected_datasets,
            "changes_detected": changes_detected,
        }

    def _group_by_dataset_id(
        self, watched_datasets: list[WatchedDataset]
    ) -> dict[str, list[WatchedDataset]]:
        grouped: dict[str, list[WatchedDataset]] = defaultdict(list)
        for watched_dataset in watched_datasets:
            grouped[watched_dataset.dataset_id].append(watched_dataset)
        return dict(grouped)

    def _compute_quality_score(self, dataset: DatasetDetailResponse) -> int:
        # Le score est recalculé à partir du snapshot courant, pas relu depuis le cache.
        # Cela permet de comparer l'état observé maintenant avec last_known_quality_score.
        indicators = compute_indicators(
            DatasetIndicatorInput(
                description=dataset.description,
                tags=list(dataset.tags or []),
                created=dataset.created,
                modified=dataset.modified,
                resource_formats=[
                    resource.format for resource in dataset.resources if resource.format
                ],
                resource_count=len(dataset.resources),
            )
        )
        return indicators.quality_score

    def _log_metadata_changes(
        self,
        watched_items: list[WatchedDataset],
        dataset_id: str,
        current_metadata_modified: str | None,
    ) -> int:
        for watched_item in watched_items:
            if watched_item.last_known_metadata_modified == current_metadata_modified:
                continue
            self._changelog_repository.insert(
                dataset_id=dataset_id,
                change_type="metadata_updated",
                previous_value=watched_item.last_known_metadata_modified,
                new_value=current_metadata_modified,
                detected_at=self._now_iso(),
            )
            return 1
        return 0

    def _log_resource_count_changes(
        self,
        watched_items: list[WatchedDataset],
        dataset_id: str,
        current_resource_count: int,
    ) -> int:
        for watched_item in watched_items:
            previous_resource_count = watched_item.last_known_resource_count
            if previous_resource_count is None or previous_resource_count == current_resource_count:
                continue
            change_type = "resource_added"
            if current_resource_count < previous_resource_count:
                change_type = "resource_removed"
            self._changelog_repository.insert(
                dataset_id=dataset_id,
                change_type=change_type,
                previous_value=str(previous_resource_count),
                new_value=str(current_resource_count),
                detected_at=self._now_iso(),
            )
            return 1
        return 0

    def _log_quality_changes(
        self,
        watched_items: list[WatchedDataset],
        dataset_id: str,
        current_quality_score: int,
    ) -> int:
        for watched_item in watched_items:
            previous_quality_score = watched_item.last_known_quality_score
            if previous_quality_score is None:
                continue
            if previous_quality_score - current_quality_score <= _QUALITY_DROP_THRESHOLD:
                continue
            self._changelog_repository.insert(
                dataset_id=dataset_id,
                change_type="quality_degraded",
                previous_value=str(previous_quality_score),
                new_value=str(current_quality_score),
                detected_at=self._now_iso(),
            )
            return 1
        return 0

    def _log_link_changes(self, dataset_id: str, resources: Sequence[object]) -> int:
        changes = 0
        for resource in resources:
            url = getattr(resource, "url", None)
            if not url:
                continue
            is_broken, detail = self._check_link(url)
            if not is_broken:
                continue
            self._changelog_repository.insert(
                dataset_id=dataset_id,
                change_type="link_broken",
                previous_value=url,
                new_value=detail,
                detected_at=self._now_iso(),
            )
            changes += 1
        return changes

    def _check_link(self, url: str) -> tuple[bool, str]:
        try:
            response = httpx.head(
                url, timeout=_RESOURCE_HEAD_TIMEOUT_SECONDS, follow_redirects=True
            )
        except httpx.TimeoutException:
            return True, "timeout"
        except httpx.HTTPError as exc:
            return True, exc.__class__.__name__

        if response.status_code >= 400:
            return True, str(response.status_code)
        return False, str(response.status_code)

    def _now_iso(self) -> str:
        return datetime.now(UTC).isoformat()

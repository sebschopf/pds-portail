"""Cas d'usage d'execution d'un cycle de synchronisation CKAN complet.

Extrait depuis ``main.py`` et ``router.py`` (PDS-45) pour eliminer
la duplication et permettre le test unitaire du cycle complet.
"""

import logging
import time as time_module
from datetime import UTC, datetime
from typing import Protocol

from app.application.errors.ingestion import CkanRateLimitError, CkanTimeoutError
from app.application.ports.cache_repository import CacheRepositoryPort
from app.application.ports.ckan_client import CkanClientPort
from app.application.use_cases.sync_ckan_batch import SyncCkanBatchUseCase
from app.core.config import Settings

logger = logging.getLogger(__name__)


class DetectChangesExecutorPort(Protocol):
    """Contrat minimal pour déclencher la détection des changements en fin de cycle."""

    def execute(self) -> dict[str, int]: ...


class SendAlertsExecutorPort(Protocol):
    """Contrat minimal pour envoyer les alertes en fin de cycle."""

    def execute(self) -> dict[str, int]: ...


class RunSyncCycleUseCase:
    """Execute un cycle de synchronisation CKAN (bootstrap ou differentiel).

    Centralise la logique de boucle d'ingestion auparavant dupliquee dans
    ``app/main.py`` et ``app/presentation/api/v1/router.py``.
    Conserve la responsabilite unique du cycle (SRP/ADR-003).
    """

    def __init__(
        self,
        client: CkanClientPort,
        repository: CacheRepositoryPort,
        settings: Settings,
        detect_changes_use_case: DetectChangesExecutorPort | None = None,
        send_alerts_use_case: SendAlertsExecutorPort | None = None,
    ) -> None:
        self._client = client
        self._repository = repository
        self._settings = settings
        self._detect_changes_use_case = detect_changes_use_case
        self._send_alerts_use_case = send_alerts_use_case

    def execute(self) -> dict[str, int | str]:
        """Execute un cycle de sync et retourne les metriques du cycle.

        Returns:
            Dictionnaire de metriques : synced_datasets, synced_organizations,
            synced_resources, errors, mode, duration_ms, started_at, completed_at.
        """
        started_at = datetime.now(UTC)
        metrics: dict[str, int | str] = {
            "synced_datasets": 0,
            "synced_organizations": 0,
            "synced_resources": 0,
            "errors": 0,
            "mode": "bootstrap",
            "duration_ms": 0,
            "started_at": started_at.isoformat(),
            "completed_at": "",
        }

        batch_use_case = SyncCkanBatchUseCase(
            client=self._client,
            repository=self._repository,
        )

        raw_offset = self._repository.get_sync_state("ckan_offset")
        current_offset = int(raw_offset) if raw_offset and raw_offset.isdigit() else 0
        last_full_sync = self._repository.get_sync_state("last_full_sync")

        # Mode differentiel (PDS-53) : si le catalogue a deja ete entierement charge
        # (offset remis a 0 apres avoir atteint la fin), on ne recupere que les datasets
        # modifies depuis la derniere synchro.
        if last_full_sync and current_offset == 0:
            metrics["mode"] = "differential"
            logger.info("CKAN sync: mode differentiel active, modified_since=%s", last_full_sync)
            try:
                batch = batch_use_case.execute(
                    start=0,
                    rows=self._settings.ckan_sync_batch_rows,
                    modified_since=last_full_sync,
                )
            except (CkanTimeoutError, CkanRateLimitError) as exc:
                logger.warning("CKAN diff sync echec: %s", exc)
                metrics["errors"] = 1
                metrics["completed_at"] = datetime.now(UTC).isoformat()
                metrics["duration_ms"] = int(
                    (datetime.now(UTC) - started_at).total_seconds() * 1000
                )
                self._save_metrics(metrics)
                return metrics

            synced_count = len(batch.datasets)
            metrics["synced_datasets"] = synced_count
            metrics["synced_organizations"] = len(batch.organizations)
            metrics["synced_resources"] = len(batch.resources)

            now = datetime.now(UTC).isoformat()
            self._repository.set_sync_state("last_full_sync", now)
            logger.info(
                "CKAN diff sync finished: synced_datasets=%s, new last_full_sync=%s",
                synced_count,
                now,
            )
            if synced_count > 0:
                self._repository.rebuild_facets()

            metrics["completed_at"] = now
            metrics["duration_ms"] = int((datetime.now(UTC) - started_at).total_seconds() * 1000)
            self._save_metrics(metrics)
            return metrics

        logger.info("CKAN sync starting at offset=%s", current_offset)

        total_synced = 0
        total_orgs = 0
        total_resources = 0
        error_count = 0

        for batch_index in range(self._settings.ckan_sync_max_batches_per_run):
            # La resilience reseau (backoff, retry) est dans le client CKAN.
            # Le use case ne fait que skipper ce que le client n'a pas pu recuperer
            # apres epuisement des tentatives.
            batch = batch_use_case.execute(
                start=current_offset, rows=self._settings.ckan_sync_batch_rows
            )
            synced_count = len(batch.datasets)
            total_synced += synced_count
            total_orgs += len(batch.organizations)
            total_resources += len(batch.resources)

            # Si le lot est partiel, on a atteint la fin du catalogue CKAN.
            if synced_count < self._settings.ckan_sync_batch_rows:
                current_offset = 0
                now = datetime.now(UTC).isoformat()
                self._repository.set_sync_state("last_full_sync", now)
                logger.info(
                    "CKAN sync: fin du catalogue atteinte, offset reinitialise a 0, "
                    "last_full_sync=%s",
                    now,
                )
            else:
                current_offset += self._settings.ckan_sync_batch_rows

            self._repository.set_sync_state("ckan_offset", str(current_offset))

            if synced_count < self._settings.ckan_sync_batch_rows:
                break

            if batch_index < self._settings.ckan_sync_max_batches_per_run - 1:
                time_module.sleep(self._settings.ckan_sync_batch_delay_seconds)

        if total_synced > 0:
            self._repository.rebuild_facets()

        if self._detect_changes_use_case is not None:
            self._detect_changes_use_case.execute()

        if self._send_alerts_use_case is not None:
            self._send_alerts_use_case.execute()

        metrics["synced_datasets"] = total_synced
        metrics["synced_organizations"] = total_orgs
        metrics["synced_resources"] = total_resources
        metrics["errors"] = error_count
        metrics["completed_at"] = datetime.now(UTC).isoformat()
        metrics["duration_ms"] = int((datetime.now(UTC) - started_at).total_seconds() * 1000)

        logger.info(
            "CKAN sync cycle finished: synced_datasets=%s next_offset=%s",
            total_synced,
            current_offset,
        )

        self._save_metrics(metrics)
        return metrics

    def _save_metrics(self, metrics: dict[str, int | str]) -> None:
        """Persiste les metriques du cycle dans la table sync_metrics (PDS-45)."""
        self._repository.add_sync_metrics(metrics)

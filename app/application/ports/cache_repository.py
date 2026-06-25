from typing import Any, Protocol

from app.domain.ckan_normalized import NormalizedBatch


class CacheRepositoryPort(Protocol):
    def upsert_normalized_batch(self, batch: NormalizedBatch) -> None:
        """Persist a normalized CKAN batch without duplicating existing entities."""

    def get_sync_state(self, key: str) -> str | None:
        """Lit un etat persistant (ex: offset CKAN) ou retourne None si absent."""

    def set_sync_state(self, key: str, value: str) -> None:
        """Ecrit un etat persistant avec horodatage de mise a jour."""

    def rebuild_facets(self) -> None:
        """Reconstruit le cache de facettes apres ingestion (PDS-44)."""

    def add_sync_metrics(self, metrics: dict[str, Any]) -> None:
        """Persiste les metriques d'un cycle de sync termine (PDS-45)."""

    def get_sync_state_updated_at(self, key: str) -> str | None:
        """Retourne l'horodatage de derniere mise a jour d'un etat persistant.

        Retourne None si la cle n'existe pas. Permet d'exposer l'age de
        l'offset sans acces direct a la base de donnees (ADR-003).
        """

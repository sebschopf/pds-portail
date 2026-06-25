from typing import Protocol

from app.domain.ckan_normalized import NormalizedBatch


class CacheRepositoryPort(Protocol):
    def upsert_normalized_batch(self, batch: NormalizedBatch) -> None:
        """Persist a normalized CKAN batch without duplicating existing entities."""

    def get_sync_state(self, key: str) -> str | None:
        """Lit un etat persistant (ex: offset CKAN) ou retourne None si absent."""

    def set_sync_state(self, key: str, value: str) -> None:
        """Ecrit un etat persistant avec horodatage de mise a jour."""

"""Port de lecture minimal du cache pour les endpoints de sante."""

from typing import Protocol

from app.domain.cache_health import CacheCounts
from app.presentation.api.v1.schemas import DatasetDetailResponse


class CacheReadRepositoryPort(Protocol):
    """Contrat de lecture interne du cache local."""

    def get_last_sync_timestamp(self) -> str | None:
        """Retourne le dernier horodatage de synchronisation disponible."""
        ...

    def get_cache_counts(self) -> CacheCounts:
        """Retourne les compteurs minimaux pour verifier le cache."""
        ...

    def get_dataset(self, dataset_id: str) -> DatasetDetailResponse | None:
        """Retourne le detail complet d'un dataset present dans le cache."""
        ...

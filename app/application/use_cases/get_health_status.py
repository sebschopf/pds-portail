"""Cas d'usage de lecture de l'etat de sante du service/cache."""

from app.application.ports.cache_read_repository import CacheReadRepositoryPort
from app.domain.cache_health import CacheHealthSnapshot


class GetHealthStatusUseCase:
    """Construit la reponse de sante minimale pour l'API interne."""

    def __init__(self, repository: CacheReadRepositoryPort) -> None:
        self._repository = repository

    def execute(self) -> CacheHealthSnapshot:
        """Retourne l'etat service + dernier sync + compteurs cache."""

        counts = self._repository.get_cache_counts()
        last_sync = self._repository.get_last_sync_timestamp()
        return CacheHealthSnapshot(
            status="ok",
            last_sync=last_sync,
            cache_populated=counts.datasets > 0,
            counts=counts,
        )

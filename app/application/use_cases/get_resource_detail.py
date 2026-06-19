"""Cas d'usage de detail ressource.

Orchestre la lecture du detail d'une ressource avec reference au dataset.
"""

from app.application.ports.search_repository import DatasetDetailRepositoryPort
from app.presentation.api.v1.schemas import ResourceDetailResponse


class GetResourceDetailUseCase:
    """Retourne le detail d'une ressource avec reference au dataset."""

    def __init__(self, repository: DatasetDetailRepositoryPort) -> None:
        self._repository = repository

    def execute(self, resource_id: str) -> ResourceDetailResponse | None:
        """Retourne le detail de la ressource ou None s'elle n'existe pas.

        Args:
            resource_id: ID de la ressource (UUID CKAN)

        Returns:
            ResourceDetailResponse avec metadata et reference au dataset,
            ou None si la ressource n'existe pas
        """

        return self._repository.get_resource(resource_id)

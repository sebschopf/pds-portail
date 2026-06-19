"""Cas d'usage de detail dataset.

Orchestre la lecture du detail complet d'un dataset avec ressources et indicateurs.
"""

from app.application.ports.search_repository import DatasetDetailRepositoryPort
from app.presentation.api.v1.schemas import DatasetDetailResponse


class GetDatasetDetailUseCase:
    """Retourne le detail complet d'un dataset avec structure et ressources."""

    def __init__(self, repository: DatasetDetailRepositoryPort) -> None:
        self._repository = repository

    def execute(self, dataset_id: str) -> DatasetDetailResponse | None:
        """Retourne le detail du dataset ou None s'il n'existe pas.

        Args:
            dataset_id: ID du dataset (UUID CKAN)

        Returns:
            DatasetDetailResponse avec toutes les ressources et indicateurs,
            ou None si le dataset n'existe pas
        """

        return self._repository.get_dataset(dataset_id)

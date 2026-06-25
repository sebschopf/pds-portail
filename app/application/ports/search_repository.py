"""Port de recherche et detail dataset.

Abstraire la logique d'acces a la donnee pour les endpoints de recherche et
detail sans exposer les details SQLAlchemy ou schema CKAN.
"""

from typing import Protocol

from app.presentation.api.v1.schemas import (
    CompareItem,
    DatasetDetailResponse,
    ResourceDetailResponse,
    SearchResponse,
)


class SearchRepositoryPort(Protocol):
    """Contrat pour chercher et filtrer les datasets."""

    def search(
        self,
        query: str | None = None,
        offset: int = 0,
        limit: int = 20,
        org_filter: str | None = None,
        format_filter: str | None = None,
        tag_filter: str | None = None,
        sort: str = "modified_desc",
    ) -> SearchResponse:
        """Recherche les datasets avec pagination et filtres optionnels.

        Args:
            query: Texte libre (titre, description)
            offset: Position dans les resultats
            limit: Nombre de resultats par page
            org_filter: Filtrer par organisation (slugname)
            format_filter: Filtrer par format de ressource
            tag_filter: Filtrer par tag exact
            sort: Strategie de tri explicite

        Returns:
            SearchResponse paginee avec facettes
        """
        ...


class DatasetDetailRepositoryPort(Protocol):
    """Contrat pour lire un dataset et ses ressources."""

    def get_dataset(self, dataset_id: str) -> DatasetDetailResponse | None:
        """Retourne le detail complet d'un dataset avec indicateurs et structure."""
        ...

    def get_resource(self, resource_id: str) -> ResourceDetailResponse | None:
        """Retourne le detail d'une ressource avec reference au dataset."""
        ...


class CompareRepositoryPort(Protocol):
    """Contrat pour la comparaison guidee de datasets (PDS-43).

    Charge plusieurs datasets en une seule requete batch pour les comparer
    sur des criteres homogenes (qualite, fraicheur, formats, etc.).
    """

    def get_by_ids(self, ids: list[str]) -> list[CompareItem]:
        """Charge les datasets comparables en batch (1 seul round-trip DB).

        Args:
            ids: Liste de 2 a 4 IDs de datasets.

        Returns:
            Liste de CompareItem (ordre preserve). Les IDs inexistants sont
            silencieusement ignores (pas d'erreur).
        """
        ...

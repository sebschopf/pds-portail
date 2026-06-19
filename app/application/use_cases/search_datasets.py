"""Cas d'usage de recherche dataset.

Orchestre une requete de recherche paginee avec filtres et facettes.
"""

from app.application.ports.search_repository import SearchRepositoryPort
from app.presentation.api.v1.schemas import SearchResponse


class SearchDatasetsUseCase:
    """Effectue une recherche dataset paginee avec filtres optionnels."""

    def __init__(self, repository: SearchRepositoryPort) -> None:
        self._repository = repository

    def execute(
        self,
        query: str | None = None,
        offset: int = 0,
        limit: int = 20,
        org_filter: str | None = None,
        format_filter: str | None = None,
        sort: str = "modified_desc",
    ) -> SearchResponse:
        """Recherche les datasets avec pagination et filtres.

        Args:
            query: Texte libre (titre, description, tags)
            offset: Position dans les resultats (defaut 0)
            limit: Nombre de resultats par page (defaut 20, max 100)
            org_filter: Filtrer par ID organisation (optionnel)
            format_filter: Filtrer par format (CSV, JSON, etc) (optionnel)
            sort: Strategie de tri explicite

        Returns:
            SearchResponse paginee avec facettes d'agregation
        """

        # Valider et normaliser les parametres
        limit = min(limit, 100)  # Cap a 100 par page
        offset = max(offset, 0)

        return self._repository.search(
            query=query,
            offset=offset,
            limit=limit,
            org_filter=org_filter,
            format_filter=format_filter,
            sort=sort,
        )

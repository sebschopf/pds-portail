"""Cas d'usage de recherche dataset.

Orchestre une requete de recherche paginee avec filtres et facettes.
"""

from app.application.ports.search_repository import SearchRepositoryPort
from app.domain.query_expansion import expand_query
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
        tag_filter: str | None = None,
        sort: str = "modified_desc",
    ) -> SearchResponse:
        """Recherche les datasets avec pagination et filtres.

        Args:
            query: Texte libre (titre, description)
            offset: Position dans les resultats (defaut 0)
            limit: Nombre de resultats par page (defaut 20, max 100)
            org_filter: Filtrer par ID organisation (optionnel)
            format_filter: Filtrer par format (CSV, JSON, etc) (optionnel)
            tag_filter: Filtrer par tag specifique (optionnel)
            sort: Strategie de tri explicite

        Returns:
            SearchResponse paginee avec facettes d'agregation
        """

        # Valider et normaliser les parametres
        limit = min(limit, 100)  # Cap a 100 par page
        offset = max(offset, 0)

        expanded_terms: list[str] | None = None
        if query and query.strip():
            expansion = expand_query(query)
            if expansion.expanded_terms:
                expanded_terms = expansion.expanded_terms

        return self._repository.search(
            query=query,
            expanded_terms=expanded_terms,
            offset=offset,
            limit=limit,
            org_filter=org_filter,
            format_filter=format_filter,
            tag_filter=tag_filter,
            sort=sort,
        )

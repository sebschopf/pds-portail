"""Use case PDS-43 : Comparaison guidee de datasets.

Valide la requete (2 a 4 IDs), collecte les datasets en batch, et retourne
une reponse structuree pour le tableau comparatif.
"""

from __future__ import annotations

from app.application.ports.search_repository import CompareRepositoryPort
from app.presentation.api.v1.schemas import (
    MAX_COMPARE_IDS,
    CompareRequest,
    CompareResponse,
)


class InvalidCompareRequestError(ValueError):
    """Requete de comparaison invalide (IDs manquants ou hors bornes)."""


class CompareDatasetsUseCase:
    """Collecte et normalise N datasets pour affichage comparatif.

    Ne fait pas de calcul supplementaire : se contente d'agreger les champs
    deja disponibles (qualite, fraicheur, formats, etc.) depuis le cache.
    """

    def __init__(self, repository: CompareRepositoryPort) -> None:
        self._repo = repository

    def execute(self, request: CompareRequest) -> CompareResponse:
        """Valide la requete et retourne les datasets comparables.

        Args:
            request: Liste de 2 a 4 IDs de datasets.

        Returns:
            CompareResponse avec les items trouves (ordre preserve).

        Raises:
            InvalidCompareRequestError: Si moins de 2 IDs valides.
        """
        ids = [id_.strip() for id_ in request.ids if id_ and id_.strip()]
        if len(ids) < 2:
            raise InvalidCompareRequestError(
                f"Au moins 2 IDs sont requis pour une comparaison (recu: {len(ids)})"
            )
        if len(ids) > MAX_COMPARE_IDS:
            raise InvalidCompareRequestError(
                f"Maximum {MAX_COMPARE_IDS} datasets comparables (recu: {len(ids)})"
            )

        items = self._repo.get_by_ids(ids)

        if len(items) < 2:
            raise InvalidCompareRequestError(
                f"Au moins 2 datasets valides sont requis (trouve: {len(items)})"
            )

        return CompareResponse(items=items)

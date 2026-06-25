"""Port applicatif pour la lecture des datasets depuis CKAN."""

from typing import Protocol

from app.application.ports.ckan_types import CkanPackageSearchResponse


class CkanClientPort(Protocol):
    """Contrat stable attendu par les cas d'usage de synchronisation."""

    def fetch_packages_batch(
        self,
        start: int,
        rows: int = 100,
        modified_since: str | None = None,
    ) -> CkanPackageSearchResponse:
        """Recupere une page CKAN deja validee et typée.

        Si ``modified_since`` est fourni (ISO 8601), filtre sur
        ``metadata_modified`` pour la synchro differentielle.
        """
        ...

"""Port applicatif pour la lecture des datasets depuis CKAN."""

from typing import Protocol

from app.application.ports.ckan_types import CkanPackageSearchResponse


class CkanClientPort(Protocol):
    """Contrat stable attendu par les cas d'usage de synchronisation."""

    def fetch_packages_batch(self, start: int, rows: int = 100) -> CkanPackageSearchResponse:
        """Recupere une page CKAN deja validee et typée."""
        ...

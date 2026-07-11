"""Port de normalisation — contrat pour traduire un payload source en entités domaine.

Permet de brancher de nouvelles sources (I14Y, metadata.swiss) sans modifier
le pipeline d'ingestion. Chaque source fournit son propre normalisateur qui
respecte ce contrat.
"""

from typing import Protocol

from app.application.ports.ckan_types import CkanPackageSearchResponse
from app.domain.ckan_normalized import NormalizedBatch


class NormalizerPort(Protocol):
    """Contrat de normalisation d'un payload source vers les entités domaine.

    Le paramètre ``source`` est passé au constructeur et propagé dans chaque
    entité normalisée (Organization, Dataset, Resource). Cela permet de
    distinguer la provenance dans le cache et les futures API.
    """

    def __init__(self, source: str = "ckan") -> None: ...

    def normalize(self, payload: CkanPackageSearchResponse) -> NormalizedBatch:
        """Traduit un payload source en entités domaine normalisées."""
        ...

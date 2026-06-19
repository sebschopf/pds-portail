"""Contrats de forme des payloads CKAN bruts (TypedDict).

Separes des validateurs (ckan_payloads.py) pour respecter le principe SRP :
les types sont des declarations pures, les validateurs transforment l'objet
``object`` en instances de ces types.

Chaque TypedDict declare en ``total=False`` pour ne decoder que les champs
exploites par le MVP sans forcer la presence de champs CKAN optionnels.
"""

from typing import TypedDict


class CkanTagPayload(TypedDict, total=False):
    """Representation minimale d'un tag CKAN utile a la normalisation."""

    name: str
    display_name: str


class CkanOrganizationPayload(TypedDict, total=False):
    """Fragment d'organisation CKAN consomme par le batch de synchro."""

    id: str
    name: str
    title: str
    description: str
    image_url: str
    url: str


class CkanResourcePayload(TypedDict, total=False):
    """Fragment de ressource CKAN persiste dans le cache local."""

    id: str
    package_id: str
    name: str
    description: str
    format: str
    download_url: str
    url: str
    size: int
    created: str
    last_modified: str


class CkanPackagePayload(TypedDict, total=False):
    """Jeu minimal de champs d'un dataset CKAN utile au domaine."""

    id: str
    title: str
    notes: str
    metadata_created: str
    metadata_modified: str
    url: str
    organization: CkanOrganizationPayload
    tags: list[CkanTagPayload]
    resources: list[CkanResourcePayload]


class CkanPackageSearchResult(TypedDict, total=False):
    """Contenu de ``result`` renvoye par ``package_search``."""

    results: list[CkanPackagePayload]


class CkanPackageSearchResponse(TypedDict, total=False):
    """Reponse CKAN typée pour la couche application."""

    result: CkanPackageSearchResult

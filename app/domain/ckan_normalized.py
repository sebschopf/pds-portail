"""Entites domaine normalisees pour le cache CKAN local."""

from dataclasses import dataclass, field


def _empty_tags() -> list[str]:
    """Fournit une liste de tags typée pour les dataclasses strictes."""

    return []


@dataclass(slots=True)
class Organization:
    """Organisation productrice exposee par CKAN."""

    id: str
    name: str
    description: str | None = None
    ckan_url: str | None = None
    last_synced: str | None = None
    source: str = "ckan"


@dataclass(slots=True)
class Dataset:
    """Dataset normalise pret a etre persiste puis expose par l'API."""

    id: str
    org_id: str
    title: str
    description: str | None = None
    tags: list[str] = field(default_factory=_empty_tags)
    created: str | None = None
    modified: str | None = None
    quality_score: int | None = None
    completeness: int | None = None
    freshness_days: int | None = None
    ckan_url: str | None = None
    normalized_at: str | None = None
    source: str = "ckan"


@dataclass(slots=True)
class Resource:
    """Ressource rattachee a un dataset CKAN."""

    id: str
    dataset_id: str
    name: str
    format: str | None = None
    url: str | None = None
    size_bytes: int | None = None
    created: str | None = None
    last_modified: str | None = None
    source: str = "ckan"


@dataclass(slots=True)
class NormalizedBatch:
    """Resultat normalise d'une page CKAN synchronisee."""

    organizations: list[Organization]
    datasets: list[Dataset]
    resources: list[Resource]

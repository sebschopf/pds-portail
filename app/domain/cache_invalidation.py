"""Stratégies d'invalidation ciblée du cache multi-niveaux (PDS-46).

Définit les clés de cache versionnées par type d'endpoint et les règles
d'invalidation déclenchées sur les events de synchronisation CKAN.
"""

from dataclasses import dataclass
from enum import StrEnum


class CacheEndpointType(StrEnum):
    """Type d'endpoint pour le versioning des clés de cache."""

    SEARCH = "search"
    DATASET_DETAIL = "dataset_detail"
    RESOURCE_DETAIL = "resource_detail"
    COMPARE = "compare"
    FACETS = "facets"


# Version de schéma API — incrémenter en cas de changement de contrat
# pour forcer l'invalidation globale du cache applicatif.
CACHE_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class CacheKey:
    """Clé de cache versionnée et typée.

    Le format est: v{version}:{endpoint_type}:{fingerprint}
    où fingerprint est déterministe pour la requête (hash des paramètres).
    """

    endpoint_type: CacheEndpointType
    fingerprint: str
    version: int = CACHE_SCHEMA_VERSION

    def to_string(self) -> str:
        return f"v{self.version}:{self.endpoint_type.value}:{self.fingerprint}"

    @classmethod
    def from_string(cls, key: str) -> "CacheKey":
        """Parse une clé de cache au format v{version}:{type}:{fingerprint}."""
        parts = key.split(":", 2)
        version = int(parts[0][1:])  # Skip 'v'
        endpoint_type = CacheEndpointType(parts[1])
        fingerprint = parts[2]
        return cls(endpoint_type=endpoint_type, fingerprint=fingerprint, version=version)


def build_search_cache_key(
    query: str | None,
    offset: int,
    limit: int,
    org_filter: str | None,
    format_filter: str | None,
    tag_filter: str | None,
    sort: str,
) -> str:
    """Construit une clé de cache déterministe pour une requête search.

    La clé est stable quel que soit l'ordre d'appel des paramètres optionnels.
    Tous les paramètres None sont omis du fingerprint.
    """
    from hashlib import sha256

    parts = [
        f"q={query or ''}",
        f"o={offset}",
        f"l={limit}",
        f"org={org_filter or ''}",
        f"fmt={format_filter or ''}",
        f"tag={tag_filter or ''}",
        f"sort={sort}",
    ]
    raw = "|".join(parts)
    fingerprint = sha256(raw.encode()).hexdigest()[:16]
    return CacheKey(endpoint_type=CacheEndpointType.SEARCH, fingerprint=fingerprint).to_string()


def build_dataset_detail_cache_key(dataset_id: str) -> str:
    """Construit une clé de cache pour le détail d'un dataset."""
    fingerprint = dataset_id.lower()
    return CacheKey(
        endpoint_type=CacheEndpointType.DATASET_DETAIL, fingerprint=fingerprint
    ).to_string()


def build_resource_detail_cache_key(resource_id: str) -> str:
    """Construit une clé de cache pour le détail d'une ressource."""
    fingerprint = resource_id.lower()
    return CacheKey(
        endpoint_type=CacheEndpointType.RESOURCE_DETAIL, fingerprint=fingerprint
    ).to_string()


def build_compare_cache_key(ids: list[str]) -> str:
    """Construit une clé de cache pour une requête compare."""
    from hashlib import sha256

    sorted_ids = sorted(ids)
    raw = ",".join(sorted_ids)
    fingerprint = sha256(raw.encode()).hexdigest()[:16]
    return CacheKey(endpoint_type=CacheEndpointType.COMPARE, fingerprint=fingerprint).to_string()


# --- Règles d'invalidation ---


def invalidation_scope_after_sync(synced_dataset_ids: list[str]) -> dict[CacheEndpointType, bool]:
    """Détermine le scope d'invalidation après un cycle de sync.

    Retourne un dict indiquant quels types de cache doivent être invalidés
    selon les IDs de datasets modifiés pendant la sync.

    Règles (ADR-007, ADR-023):
    - Si >= 1 dataset sync: invalider SEARCH (les résultats peuvent changer)
    - Si >= 1 dataset sync: invalider FACETS (les compteurs peuvent changer)
    - Invalider DATASET_DETAIL uniquement pour les datasets spécifiques modifiés
    - COMPARE: invalidé seulement si un des datasets comparés a changé
    - RESOURCE_DETAIL: invalidé seulement si la ressource a changé
    """
    scope: dict[CacheEndpointType, bool] = {
        CacheEndpointType.SEARCH: len(synced_dataset_ids) > 0,
        CacheEndpointType.DATASET_DETAIL: len(synced_dataset_ids) > 0,
        CacheEndpointType.RESOURCE_DETAIL: len(synced_dataset_ids) > 0,
        CacheEndpointType.COMPARE: len(synced_dataset_ids) > 0,
        CacheEndpointType.FACETS: len(synced_dataset_ids) > 0,
    }
    return scope


def is_cache_stale(created_at_iso: str, ttl_seconds: int) -> bool:
    """Vérifie si une entrée de cache a dépassé son TTL.

    Args:
        created_at_iso: Horodatage ISO 8601 de création de l'entrée
        ttl_seconds: Durée de vie en secondes

    Returns:
        True si l'entrée est périmée, False sinon
    """
    from datetime import UTC, datetime

    try:
        created = datetime.fromisoformat(created_at_iso)
        age = (datetime.now(UTC) - created).total_seconds()
        return age > ttl_seconds
    except (ValueError, TypeError):
        return True  # Entrée invalide → considérée comme stale

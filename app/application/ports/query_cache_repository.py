"""Port de cache applicatif multi-niveaux pour reponses d'endpoint (PDS-46).

Abstrait le stockage, la lecture, l'invalidation et l'instrumentation du cache
applicatif sans exposer les details SQLite.
"""

from typing import Protocol

from app.domain.cache_invalidation import CacheEndpointType


class CacheStats:
    """Statistiques de hit/miss du cache applicatif."""

    def __init__(self, hits: int, misses: int, stale_entries: int, total_entries: int) -> None:
        self.hits = hits
        self.misses = misses
        self.stale_entries = stale_entries
        self.total_entries = total_entries

    @property
    def hit_ratio(self) -> float:
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total


class QueryCacheRepositoryPort(Protocol):
    """Contrat de cache applicatif avec TTL et invalidation fine."""

    def get(self, cache_key: str, ttl_seconds: int) -> str | None:
        """Lit une entrée de cache si elle existe et n'est pas périmée.

        Args:
            cache_key: Clé versionnée (format v{ver}:{type}:{fingerprint})
            ttl_seconds: Durée de vie maximale en secondes

        Returns:
            Le JSON sérialisé si trouvé et frais, None sinon.
        """
        ...

    def set(self, cache_key: str, endpoint_type: CacheEndpointType, response_json: str) -> None:
        """Écrit une réponse dans le cache applicatif.

        Args:
            cache_key: Clé versionnée
            endpoint_type: Type d'endpoint pour l'invalidation ciblée
            response_json: Réponse sérialisée en JSON
        """
        ...

    def invalidate_by_endpoint_type(self, endpoint_type: CacheEndpointType) -> int:
        """Invalide toutes les entrées d'un type d'endpoint donné.

        Args:
            endpoint_type: Type à invalider (ex: SEARCH après sync CKAN)

        Returns:
            Nombre d'entrées supprimées.
        """
        ...

    def invalidate_by_key(self, cache_key: str) -> bool:
        """Invalide une entrée spécifique par sa clé.

        Returns:
            True si l'entrée existait, False sinon.
        """
        ...

    def reset_stats(self) -> None:
        """Réinitialise les compteurs hit/miss (après redémarrage ou purge)."""
        ...

    def get_stats(self) -> CacheStats:
        """Retourne les statistiques actuelles de hit/miss."""
        ...

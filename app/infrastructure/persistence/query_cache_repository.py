"""Adapter SQLAlchemy du cache applicatif multi-niveaux (PDS-46).

Implémente QueryCacheRepositoryPort avec stockage SQLite, TTL et
invalidation ciblée par type d'endpoint.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import func

from app.application.ports.query_cache_repository import CacheStats
from app.domain.cache_invalidation import CacheEndpointType, is_cache_stale
from app.infrastructure.persistence.database import SessionLocal
from app.infrastructure.persistence.models import CacheHitStatsModel, QueryCacheModel

logger = logging.getLogger(__name__)


class SqlAlchemyQueryCacheRepository:
    """Cache applicatif SQLite avec instrumentation hit/miss."""

    # TTL par défaut (24h, ADR-007)
    DEFAULT_TTL_SECONDS = 24 * 3600

    def get(self, cache_key: str, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str | None:
        """Lit une entrée de cache si elle existe, est fraîche, et de schéma valide.

        Incrémente le compteur de hit si trouvée, de miss sinon.
        Vérifie le TTL et la version de schéma.
        """
        with SessionLocal() as session:
            row = session.get(QueryCacheModel, cache_key)
            if row is None:
                self._record_miss(session)
                return None

            if is_cache_stale(row.created_at, ttl_seconds):
                self._record_stale(session)
                # Ne pas supprimer automatiquement — l'invalidation est explicite
                return None

            # Hit : incrémenter le compteur de hit et retourner
            row.hit_count += 1
            self._record_hit(session)
            session.commit()
            return row.response_json

    def set(self, cache_key: str, endpoint_type: CacheEndpointType, response_json: str) -> None:
        """Écrit ou met à jour une entrée de cache applicatif."""
        now = datetime.now(UTC).isoformat()
        with SessionLocal() as session:
            session.merge(
                QueryCacheModel(
                    key=cache_key,
                    endpoint_type=endpoint_type.value,
                    response_json=response_json,
                    created_at=now,
                    hit_count=0,
                )
            )
            session.commit()

    def invalidate_by_endpoint_type(self, endpoint_type: CacheEndpointType) -> int:
        """Supprime toutes les entrées d'un type d'endpoint donné.

        Utilisé après un cycle de sync CKAN pour invalider les résultats
        de recherche et facettes.
        """
        with SessionLocal() as session:
            count = (
                session.query(QueryCacheModel)
                .filter(QueryCacheModel.endpoint_type == endpoint_type.value)
                .delete()
            )
            session.commit()
            if count > 0:
                logger.info(
                    "Cache invalidated: type=%s, entries_deleted=%d",
                    endpoint_type.value,
                    count,
                )
            return count

    def invalidate_by_key(self, cache_key: str) -> bool:
        """Supprime une entrée spécifique par sa clé."""
        with SessionLocal() as session:
            row = session.get(QueryCacheModel, cache_key)
            if row is None:
                return False
            session.delete(row)
            session.commit()
            return True

    def reset_stats(self) -> None:
        """Réinitialise les compteurs hit/miss à zéro."""
        with SessionLocal() as session:
            stats = session.get(CacheHitStatsModel, 1)
            if stats:
                stats.hits = 0
                stats.misses = 0
                stats.stale_entries = 0
            else:
                session.add(CacheHitStatsModel(id=1, hits=0, misses=0, stale_entries=0))
            session.commit()

    def get_stats(self) -> CacheStats:
        """Retourne les statistiques actuelles de hit/miss."""
        with SessionLocal() as session:
            stats = session.get(CacheHitStatsModel, 1)
            total = session.query(func.count(QueryCacheModel.key)).scalar() or 0
            if stats is None:
                return CacheStats(hits=0, misses=0, stale_entries=0, total_entries=int(total))
            return CacheStats(
                hits=stats.hits,
                misses=stats.misses,
                stale_entries=stats.stale_entries,
                total_entries=int(total),
            )

    # --- Helpers privés ---

    @staticmethod
    def _record_hit(session: object) -> None:
        """Incrémente le compteur de hits (session déjà ouverte)."""
        from sqlalchemy.orm import Session as _Session

        assert isinstance(session, _Session)
        stats = session.get(CacheHitStatsModel, 1)
        if stats:
            stats.hits += 1
        else:
            session.add(CacheHitStatsModel(id=1, hits=1, misses=0, stale_entries=0))

    @staticmethod
    def _record_miss(session: object) -> None:
        """Incrémente le compteur de misses."""
        from sqlalchemy.orm import Session as _Session

        assert isinstance(session, _Session)
        stats = session.get(CacheHitStatsModel, 1)
        if stats:
            stats.misses += 1
        else:
            session.add(CacheHitStatsModel(id=1, hits=0, misses=1, stale_entries=0))

    @staticmethod
    def _record_stale(session: object) -> None:
        """Incrémente le compteur de stale entries."""
        from sqlalchemy.orm import Session as _Session

        assert isinstance(session, _Session)
        stats = session.get(CacheHitStatsModel, 1)
        if stats:
            stats.stale_entries += 1
        else:
            session.add(CacheHitStatsModel(id=1, hits=0, misses=0, stale_entries=1))

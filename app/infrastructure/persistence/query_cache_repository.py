"""Adapter SQLAlchemy du cache applicatif multi-niveaux (PDS-46).

Implémente QueryCacheRepositoryPort avec stockage SQLite, TTL et
invalidation ciblée par type d'endpoint.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, text

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
                session.commit()
                return None

            if is_cache_stale(row.created_at, ttl_seconds):
                self._record_stale(session)
                session.commit()
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

    # --- Métriques d'usage (PDS-58) ---

    def get_top_queries(self, limit: int = 20) -> list[dict[str, Any]]:
        """Retourne les N requêtes les plus hitées, triées par hit_count décroissant.

        Colonnes retournées : query_key, endpoint_type, hit_count, created_at.
        """
        with SessionLocal() as session:
            rows = (
                session.query(
                    QueryCacheModel.key,
                    QueryCacheModel.endpoint_type,
                    QueryCacheModel.hit_count,
                    QueryCacheModel.created_at,
                )
                .order_by(QueryCacheModel.hit_count.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "query_key": row.key,
                    "endpoint_type": row.endpoint_type,
                    "hit_count": row.hit_count,
                    "created_at": row.created_at,
                }
                for row in rows
            ]

    def get_zero_result_queries(self) -> list[dict[str, Any]]:
        """Retourne les requêtes dont le response_json contient total=0.

        Parse le JSON stocké dans response_json pour extraire le champ total.
        Les requêtes avec response_json non parsable sont ignorées.
        """
        import json

        with SessionLocal() as session:
            rows = session.query(
                QueryCacheModel.key,
                QueryCacheModel.endpoint_type,
                QueryCacheModel.response_json,
                QueryCacheModel.created_at,
            ).all()
            results: list[dict[str, Any]] = []
            for row in rows:
                try:
                    payload = json.loads(row.response_json)
                except (json.JSONDecodeError, TypeError):
                    continue
                total = payload.get("total")
                if total == 0:
                    results.append(
                        {
                            "query_key": row.key,
                            "endpoint_type": row.endpoint_type,
                            "created_at": row.created_at,
                            "response_total": 0,
                        }
                    )
            return results

    # --- Helpers privés ---

    @staticmethod
    def _record_hit(session: object) -> None:
        """Incrémente le compteur de hits de manière atomique (UPDATE SQL brut)."""
        from sqlalchemy.orm import Session as _Session

        assert isinstance(session, _Session)
        session.execute(
            text(
                "INSERT INTO cache_hit_stats (id, hits, misses, stale_entries) "
                "VALUES (1, 1, 0, 0) "
                "ON CONFLICT (id) DO UPDATE SET hits = hits + 1"
            )
        )

    @staticmethod
    def _record_miss(session: object) -> None:
        """Incrémente le compteur de misses de manière atomique."""
        from sqlalchemy.orm import Session as _Session

        assert isinstance(session, _Session)
        session.execute(
            text(
                "INSERT INTO cache_hit_stats (id, hits, misses, stale_entries) "
                "VALUES (1, 0, 1, 0) "
                "ON CONFLICT (id) DO UPDATE SET misses = misses + 1"
            )
        )

    @staticmethod
    def _record_stale(session: object) -> None:
        """Incrémente le compteur de stale entries de manière atomique."""
        from sqlalchemy.orm import Session as _Session

        assert isinstance(session, _Session)
        session.execute(
            text(
                "INSERT INTO cache_hit_stats (id, hits, misses, stale_entries) "
                "VALUES (1, 0, 0, 1) "
                "ON CONFLICT (id) DO UPDATE SET stale_entries = stale_entries + 1"
            )
        )

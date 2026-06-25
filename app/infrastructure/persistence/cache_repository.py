import json
from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.domain.ckan_normalized import NormalizedBatch
from app.infrastructure.persistence.database import SessionLocal
from app.infrastructure.persistence.models import (
    DatasetModel,
    FacetsCacheModel,
    OrganizationModel,
    ResourceModel,
    SyncMetricsModel,
    SyncStateModel,
)


class SqlAlchemyCacheRepository:
    def upsert_normalized_batch(self, batch: NormalizedBatch) -> None:
        with SessionLocal() as session:
            self._upsert_organizations(session, batch)
            self._upsert_datasets(session, batch)
            self._upsert_resources(session, batch)
            session.commit()

    def get_sync_state_updated_at(self, key: str) -> str | None:
        """Retourne l'horodatage de derniere mise a jour ou None (PDS-45, ADR-003)."""
        with SessionLocal() as session:
            row = session.get(SyncStateModel, key)
            return row.updated_at if row else None

    def add_sync_metrics(self, metrics: dict[str, int | str]) -> None:
        """Persiste les metriques d'un cycle de sync termine (PDS-45).

        Stocke le volume, la duree, les erreurs et le mode pour pilotage
        et audit de l'ingestion CKAN.
        """
        import logging

        logger = logging.getLogger(__name__)
        try:
            with SessionLocal() as session:
                session.add(
                    SyncMetricsModel(
                        synced_datasets=int(metrics.get("synced_datasets", 0)),
                        synced_organizations=int(metrics.get("synced_organizations", 0)),
                        synced_resources=int(metrics.get("synced_resources", 0)),
                        errors=int(metrics.get("errors", 0)),
                        mode=str(metrics.get("mode", "bootstrap")),
                        duration_ms=int(metrics.get("duration_ms", 0)),
                        started_at=str(metrics.get("started_at", "")),
                        completed_at=str(metrics.get("completed_at", "")),
                    )
                )
                session.commit()
        except Exception:
            logger.exception("Echec de persistance des metriques de sync (non bloquant)")

    def get_sync_state(self, key: str) -> str | None:
        """Lit un etat persistant ou retourne None si la cle n'existe pas."""
        with SessionLocal() as session:
            row = session.get(SyncStateModel, key)
            return row.value if row else None

    def set_sync_state(self, key: str, value: str) -> None:
        """Ecrit un etat persistant avec horodatage de derniere mise a jour."""
        now = datetime.now(UTC).isoformat()
        with SessionLocal() as session:
            session.merge(SyncStateModel(key=key, value=value, updated_at=now))
            session.commit()

    def _upsert_organizations(self, session: Session, batch: NormalizedBatch) -> None:
        for organization in batch.organizations:
            session.merge(
                OrganizationModel(
                    id=organization.id,
                    name=organization.name,
                    description=organization.description,
                    ckan_url=organization.ckan_url,
                    last_synced=organization.last_synced,
                )
            )

    def _upsert_datasets(self, session: Session, batch: NormalizedBatch) -> None:
        for dataset in batch.datasets:
            session.merge(
                DatasetModel(
                    id=dataset.id,
                    org_id=dataset.org_id,
                    title=dataset.title,
                    description=dataset.description,
                    tags=json.dumps(dataset.tags, ensure_ascii=False),
                    created=dataset.created,
                    modified=dataset.modified,
                    quality_score=dataset.quality_score,
                    completeness=dataset.completeness,
                    freshness_days=dataset.freshness_days,
                    ckan_url=dataset.ckan_url,
                    normalized_at=dataset.normalized_at,
                )
            )

    def _upsert_resources(self, session: Session, batch: NormalizedBatch) -> None:
        for resource in batch.resources:
            session.merge(
                ResourceModel(
                    id=resource.id,
                    dataset_id=resource.dataset_id,
                    name=resource.name,
                    format=resource.format,
                    url=resource.url,
                    size_bytes=resource.size_bytes,
                    created=resource.created,
                    last_modified=resource.last_modified,
                )
            )

    def rebuild_facets(self) -> None:
        """Reconstruit le cache de facettes depuis les donnees existantes (PDS-44).

        Vide la table facets_cache puis recalcule les organisations, formats
        et tags agregees. Appele apres chaque cycle d'ingestion pour que les
        facettes reflechissent l'etat frais du cache.
        """
        now = datetime.now(UTC).isoformat()
        with SessionLocal() as session:
            # Vider les facettes existantes
            session.query(FacetsCacheModel).delete()

            # Facettes organisations
            org_rows = (
                session.query(
                    OrganizationModel.id,
                    OrganizationModel.name,
                    func.count(DatasetModel.id).label("cnt"),
                )
                .join(DatasetModel)
                .group_by(OrganizationModel.id, OrganizationModel.name)
                .order_by(func.count(DatasetModel.id).desc())
                .limit(20)
                .all()
            )
            for org_id, org_name, cnt in org_rows:
                session.add(
                    FacetsCacheModel(
                        facet_type="org",
                        name=str(org_id),
                        display_name=str(org_name),
                        count=int(cnt),
                        updated_at=now,
                    )
                )

            # Facettes formats (nombre de datasets distincts par format)
            format_rows = (
                session.query(
                    func.upper(ResourceModel.format).label("fmt"),
                    func.count(func.distinct(ResourceModel.dataset_id)).label("cnt"),
                )
                .where(ResourceModel.format.is_not(None))
                .group_by(func.upper(ResourceModel.format))
                .order_by(
                    func.count(func.distinct(ResourceModel.dataset_id)).desc(),
                )
                .all()
            )
            for fmt, cnt in format_rows:
                if fmt:
                    session.add(
                        FacetsCacheModel(
                            facet_type="format",
                            name=str(fmt),
                            display_name=None,
                            count=int(cnt),
                            updated_at=now,
                        )
                    )

            session.commit()

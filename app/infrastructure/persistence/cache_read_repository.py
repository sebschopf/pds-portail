"""Adapter SQLAlchemy des lectures minimales de cache."""

from sqlalchemy import func, select

from app.domain.cache_health import CacheCounts
from app.infrastructure.persistence.database import SessionLocal
from app.infrastructure.persistence.models import DatasetModel, OrganizationModel, ResourceModel


class SqlAlchemyCacheReadRepository:
    """Lit l'etat du cache sans exposer de details ORM aux couches hautes."""

    def get_last_sync_timestamp(self) -> str | None:
        """Prend le max de normalisation dataset, fallback sur last_synced org."""

        with SessionLocal() as session:
            latest_dataset_sync = session.scalar(select(func.max(DatasetModel.normalized_at)))
            if latest_dataset_sync:
                return latest_dataset_sync

            latest_org_sync = session.scalar(select(func.max(OrganizationModel.last_synced)))
            return latest_org_sync

    def get_cache_counts(self) -> CacheCounts:
        """Retourne les volumes minimaux du cache pour controle de peuplement."""

        with SessionLocal() as session:
            organizations = session.scalar(select(func.count()).select_from(OrganizationModel))
            datasets = session.scalar(select(func.count()).select_from(DatasetModel))
            resources = session.scalar(select(func.count()).select_from(ResourceModel))

        return CacheCounts(
            organizations=int(organizations or 0),
            datasets=int(datasets or 0),
            resources=int(resources or 0),
        )

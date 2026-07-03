"""Adapter SQLAlchemy des lectures minimales de cache."""

from sqlalchemy import func, select

from app.domain.cache_health import CacheCounts
from app.infrastructure.persistence._search_helpers import parse_tags
from app.infrastructure.persistence.database import SessionLocal
from app.infrastructure.persistence.models import DatasetModel, OrganizationModel, ResourceModel
from app.presentation.api.v1.schemas import (
    AccessMode,
    DatasetDetailResponse,
    DatasetStructure,
    ResourceResponse,
)


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

    def get_dataset(self, dataset_id: str) -> DatasetDetailResponse | None:
        """Retourne le detail complet d'un dataset depuis le cache local."""

        with SessionLocal() as session:
            dataset = session.scalar(select(DatasetModel).where(DatasetModel.id == dataset_id))
            if not dataset:
                return None

            # Ce snapshot sert de contrat de lecture partagé entre la synchro,
            # la détection des changements et les futurs adapters de lecture.
            tags = parse_tags(dataset.tags)
            resource_formats = list(
                {resource.format for resource in dataset.resources if resource.format}
            )
            structure = DatasetStructure(
                fields=[],
                formats=resource_formats,
                update_frequency=None,
                last_updated=dataset.modified,
            )

            access_modes: list[AccessMode] = []
            if dataset.resources:
                access_modes.append(
                    AccessMode(
                        type="direct_download",
                        label="Téléchargement direct",
                        description="Fichiers disponibles en téléchargement",
                    )
                )

            resources = [
                ResourceResponse(
                    id=resource.id,
                    name=resource.name,
                    format=resource.format,
                    url=resource.url,
                    size_bytes=resource.size_bytes,
                    created=resource.created,
                    last_modified=resource.last_modified,
                )
                for resource in dataset.resources
            ]

            return DatasetDetailResponse(
                id=dataset.id,
                title=dataset.title,
                description=dataset.description,
                org_id=dataset.org_id,
                org_name=dataset.organization.name,
                license=None,
                author=None,
                created=dataset.created,
                modified=dataset.modified,
                quality_score=dataset.quality_score,
                completeness=dataset.completeness,
                freshness_days=dataset.freshness_days,
                dataset_structure=structure,
                access_modes=access_modes,
                resources=resources,
                tags=tags,
                ckan_url=dataset.ckan_url,
            )

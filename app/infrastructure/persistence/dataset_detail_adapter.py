"""Adapter SQLAlchemy pour le detail dataset et ressource.

Implemente DatasetDetailRepositoryPort. Extrait de search_repository.py
originel.

ADR-003 (SRP) : cet adapter ne fait QUE le detail, pas la recherche
ni la comparaison.
"""

from __future__ import annotations

from sqlalchemy import select

from app.infrastructure.persistence._search_helpers import parse_tags
from app.infrastructure.persistence.database import SessionLocal
from app.infrastructure.persistence.models import DatasetModel, ResourceModel
from app.presentation.api.v1.schemas import (
    AccessMode,
    DatasetDetailResponse,
    DatasetStructure,
    ResourceDetailResponse,
    ResourceResponse,
)


class SqlAlchemyDatasetDetailAdapter:
    """Detail dataset + ressource depuis le cache SQLite."""

    def get_dataset(self, dataset_id: str) -> DatasetDetailResponse | None:
        """Retourne le detail complet d'un dataset avec indicateurs et ressources."""
        with SessionLocal() as session:
            dataset = session.scalar(select(DatasetModel).where(DatasetModel.id == dataset_id))
            if not dataset:
                return None

            tags = parse_tags(dataset.tags)
            resource_formats = list({r.format for r in dataset.resources if r.format})
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
                    id=r.id,
                    name=r.name,
                    format=r.format,
                    url=r.url,
                    size_bytes=r.size_bytes,
                    created=r.created,
                    last_modified=r.last_modified,
                )
                for r in dataset.resources
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

    def get_resource(self, resource_id: str) -> ResourceDetailResponse | None:
        """Retourne le detail d'une ressource avec reference au dataset."""
        with SessionLocal() as session:
            resource = session.scalar(select(ResourceModel).where(ResourceModel.id == resource_id))
            if not resource:
                return None

            return ResourceDetailResponse(
                id=resource.id,
                name=resource.name,
                format=resource.format,
                url=resource.url,
                size_bytes=resource.size_bytes,
                created=resource.created,
                last_modified=resource.last_modified,
                dataset_id=resource.dataset_id,
                dataset_title=resource.dataset.title,
            )

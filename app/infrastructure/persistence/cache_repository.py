import json

from sqlalchemy.orm import Session

from app.domain.ckan_normalized import NormalizedBatch
from app.infrastructure.persistence.database import SessionLocal
from app.infrastructure.persistence.models import DatasetModel, OrganizationModel, ResourceModel


class SqlAlchemyCacheRepository:
    def upsert_normalized_batch(self, batch: NormalizedBatch) -> None:
        with SessionLocal() as session:
            self._upsert_organizations(session, batch)
            self._upsert_datasets(session, batch)
            self._upsert_resources(session, batch)
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

"""Adapter SQLAlchemy pour la comparaison guidee de datasets (PDS-43).

Implemente CompareRepositoryPort avec chargement batch en un seul
round-trip DB. Extrait de search_repository.py originel.

ADR-003 (SRP) : cet adapter ne fait QUE la comparaison, pas la recherche
ni le detail.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.infrastructure.persistence._search_helpers import parse_tags
from app.infrastructure.persistence.database import SessionLocal
from app.infrastructure.persistence.models import DatasetModel
from app.presentation.api.v1.schemas import CompareItem


class SqlAlchemyCompareAdapter:
    """Comparaison guidee de 2 a 4 datasets en batch."""

    def get_by_ids(self, ids: list[str]) -> list[CompareItem]:
        """Charge plusieurs datasets en 1 seul round-trip DB pour comparaison.

        Optimisation batch : WHERE id IN (...) avec JOINs au lieu de
        N requetes individuelles. Les IDs inexistants sont ignores.
        """
        if not ids:
            return []

        with SessionLocal() as session:
            datasets: list[DatasetModel] = list(
                session.scalars(
                    select(DatasetModel)
                    .options(
                        joinedload(DatasetModel.organization),
                        joinedload(DatasetModel.resources),
                    )
                    .where(
                        DatasetModel.id.in_(ids),
                        DatasetModel.org_id.is_not(None),
                    )
                    .order_by(DatasetModel.id)
                )
                .unique()
                .all()
            )

            ds_map: dict[str, DatasetModel] = {ds.id: ds for ds in datasets}
            items: list[CompareItem] = []
            for ds_id in ids:
                ds = ds_map.get(ds_id)
                if ds is None:
                    continue
                tags = parse_tags(ds.tags)
                resource_formats = list(
                    {r.format for r in ds.resources if r.format and r.format.upper()}
                )
                items.append(
                    CompareItem(
                        id=ds.id,
                        title=ds.title,
                        org_name=ds.organization.name if ds.organization else None,
                        description=ds.description,
                        license=None,
                        quality_score=ds.quality_score,
                        completeness=ds.completeness,
                        freshness_days=ds.freshness_days,
                        resource_formats=resource_formats,
                        resource_count=len(ds.resources),
                        tags=tags,
                        ckan_url=ds.ckan_url,
                    )
                )
            return items

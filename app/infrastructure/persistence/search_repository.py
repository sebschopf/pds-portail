"""Adapter SQLAlchemy pour recherche et detail dataset.

Implemente les ports SearchRepositoryPort et DatasetDetailRepositoryPort
en interrogeant le cache SQLite et en normalisant les reponses.
"""

from __future__ import annotations

from collections import Counter
from typing import cast

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.infrastructure.persistence.database import SessionLocal
from app.infrastructure.persistence.models import DatasetModel, OrganizationModel, ResourceModel
from app.presentation.api.v1.schemas import (
    AccessMode,
    DatasetDetailResponse,
    DatasetStructure,
    FacetItem,
    ResourceDetailResponse,
    ResourceResponse,
    SearchDatasetItem,
    SearchFacets,
    SearchResponse,
)


class SqlAlchemySearchRepository:
    """Implemente les requetes de recherche et detail sur cache SQLite."""

    ORGANIZATION_FACET_LIMIT = 20

    def search(
        self,
        query: str | None = None,
        offset: int = 0,
        limit: int = 20,
        org_filter: str | None = None,
        format_filter: str | None = None,
        tag_filter: str | None = None,
        sort: str = "modified_desc",
    ) -> SearchResponse:
        """Cherche les datasets avec pagination et filtres.

        Effectue une recherche full-text sur titre/description et agrege
        les facettes pour l'interface de recherche. Supporte aussi filtrage
        par tag specifique en match exact sur la liste des tags.
        """

        with SessionLocal() as session:
            # Construire la clause WHERE
            base_filters: list[ColumnElement[bool]] = []
            if query:
                search_term = f"%{query.lower()}%"
                base_filters.append(
                    or_(
                        func.lower(DatasetModel.title).like(search_term),
                        func.lower(DatasetModel.description).like(search_term),
                        func.lower(OrganizationModel.name).like(search_term),
                        func.lower(DatasetModel.tags).like(search_term),
                    )
                )
            if org_filter:
                base_filters.append(DatasetModel.org_id == org_filter)
            if tag_filter:
                # Filtrer par tag exact: chercher le tag dans la liste (format JSON ou CSV)
                tag_term = f"%{tag_filter}%"
                base_filters.append(func.lower(DatasetModel.tags).like(func.lower(tag_term)))

            filters = list(base_filters)
            if format_filter:
                format_exists = (
                    select(ResourceModel.id)
                    .where(ResourceModel.dataset_id == DatasetModel.id)
                    .where(func.upper(ResourceModel.format) == format_filter.upper())
                    .exists()
                )
                filters.append(format_exists)

            # Compter les resultats totaux
            where_clause = and_(*filters) if filters else None
            total_query = select(func.count()).select_from(DatasetModel)
            if where_clause is not None:
                total_query = total_query.where(where_clause)
            total = session.scalar(total_query) or 0

            # Chercher et paginer les resultats
            dataset_query = (
                select(DatasetModel)
                .join(OrganizationModel)
                .order_by(*self._order_by_for_sort(sort))
                .offset(offset)
                .limit(limit)
            )
            if where_clause is not None:
                dataset_query = dataset_query.where(where_clause)

            datasets: list[DatasetModel] = list(session.scalars(dataset_query).all())

            # Construire les items de recherche
            search_items: list[SearchDatasetItem] = []
            for ds in datasets:
                # Parser les tags depuis la chaine JSON-like
                tags = self._parse_tags(ds.tags) if ds.tags else []

                # Compter les ressources avec le bon format (si filtre)
                resource_count = len(ds.resources)
                resource_formats = list(
                    {r.format for r in ds.resources if r.format and r.format.upper()}
                )

                search_items.append(
                    SearchDatasetItem(
                        id=ds.id,
                        title=ds.title,
                        org_name=ds.organization.name,
                        description=ds.description,
                        quality_score=ds.quality_score,
                        completeness=ds.completeness,
                        freshness_days=ds.freshness_days,
                        resource_formats=resource_formats,
                        resource_count=resource_count,
                        tags=tags,
                    )
                )

            # Agreger les facettes
            facets = self._aggregate_facets(session, base_filters)

            return SearchResponse(
                total=total,
                offset=offset,
                limit=limit,
                datasets=search_items,
                facets=facets,
            )

    def get_dataset(self, dataset_id: str) -> DatasetDetailResponse | None:
        """Retourne le detail complet d'un dataset avec indicateurs et ressources."""

        with SessionLocal() as session:
            dataset = session.scalar(select(DatasetModel).where(DatasetModel.id == dataset_id))
            if not dataset:
                return None

            # Parser les tags
            tags = self._parse_tags(dataset.tags) if dataset.tags else []

            # Construire la structure du dataset
            resource_formats = list({r.format for r in dataset.resources if r.format})
            structure = DatasetStructure(
                fields=[],  # Pas de metadata pour MVP, extensible
                formats=resource_formats,
                update_frequency=None,  # Pas de metadata pour MVP
                last_updated=dataset.modified,
            )

            # Lister les modes d'acces
            access_modes: list[AccessMode] = []
            if dataset.resources:
                access_modes.append(
                    AccessMode(
                        type="direct_download",
                        label="Téléchargement direct",
                        description="Fichiers disponibles en téléchargement",
                    )
                )

            # Normaliser les ressources
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
                license=None,  # Pas de metadata pour MVP
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

    # Helpers prive

    @staticmethod
    def _parse_tags(tags_str: str | None) -> list[str]:
        """Parse la chaine CSV-like de tags vers une liste."""
        if not tags_str:
            return []
        # Format CKAN: "tag1, tag2, tag3" ou JSON "[\"tag1\", \"tag2\"]"
        if tags_str.startswith("["):
            import json

            try:
                parsed = json.loads(tags_str)
                if isinstance(parsed, list):
                    parsed_list = cast(list[object], parsed)
                    return [str(item).strip() for item in parsed_list if str(item).strip()]
                return []
            except (json.JSONDecodeError, ValueError):
                return []
        # Fallback CSV
        return [t.strip() for t in tags_str.split(",") if t.strip()]

    @staticmethod
    def _aggregate_facets(
        session: Session,
        base_filters: list[ColumnElement[bool]],
    ) -> SearchFacets:
        """Agrege les facettes pour les filtres de recherche."""
        # Construction minimale pour MVP: orgs, formats
        # Les facettes completes requerraient l'agrégation CKAN

        # Organizations facet
        org_query = (
            select(
                OrganizationModel.id,
                OrganizationModel.name,
                func.count(DatasetModel.id).label("count"),
            )
            .join(DatasetModel)
            .group_by(OrganizationModel.id, OrganizationModel.name)
            .order_by(
                func.count(DatasetModel.id).desc(),
                OrganizationModel.name.asc(),
            )
            .limit(SqlAlchemySearchRepository.ORGANIZATION_FACET_LIMIT)
        )
        if base_filters:
            org_query = org_query.where(and_(*base_filters))

        orgs: list[FacetItem] = []
        for org_id, org_name, count in session.execute(org_query).all():
            orgs.append(
                FacetItem(
                    name=str(org_id),
                    display_name=str(org_name),
                    count=int(count),
                )
            )

        # Format facet (depuis les ressources des datasets filtres)
        format_query = (
            select(
                func.upper(ResourceModel.format).label("format_name"),
                func.count(func.distinct(ResourceModel.dataset_id)).label("count"),
            )
            .join(DatasetModel, DatasetModel.id == ResourceModel.dataset_id)
            .where(ResourceModel.format.is_not(None))
            .group_by(func.upper(ResourceModel.format))
            .order_by(func.count(func.distinct(ResourceModel.dataset_id)).desc())
        )
        if base_filters:
            format_query = format_query.where(and_(*base_filters))

        formats: list[FacetItem] = []
        for format_name, count in session.execute(format_query).all():
            if not format_name:
                continue
            formats.append(FacetItem(name=str(format_name), count=int(count)))

        # Tag facet (depuis les tags des datasets filtres)
        tag_query = select(DatasetModel.tags)
        if base_filters:
            tag_query = tag_query.where(and_(*base_filters))
        tag_counter: Counter[str] = Counter()
        for tags_str in session.scalars(tag_query).all():
            if not tags_str:
                continue
            for tag in SqlAlchemySearchRepository._parse_tags(tags_str):
                if tag:
                    tag_counter[tag] += 1
        tags: list[FacetItem] = [
            FacetItem(name=name, count=count) for name, count in tag_counter.most_common()
        ]

        return SearchFacets(organizations=orgs, formats=formats, tags=tags)

    @staticmethod
    def _order_by_for_sort(sort: str) -> tuple[ColumnElement[object], ...]:
        """Mappe la valeur sort vers des clauses SQL deterministes."""

        sort_map: dict[str, tuple[ColumnElement[object], ...]] = {
            "modified_desc": (
                cast(ColumnElement[object], DatasetModel.modified.desc()),
                cast(ColumnElement[object], DatasetModel.id.asc()),
            ),
            "modified_asc": (
                cast(ColumnElement[object], DatasetModel.modified.asc()),
                cast(ColumnElement[object], DatasetModel.id.asc()),
            ),
            "quality_desc": (
                cast(
                    ColumnElement[object],
                    func.coalesce(DatasetModel.quality_score, -1).desc(),
                ),
                cast(ColumnElement[object], DatasetModel.id.asc()),
            ),
            "quality_asc": (
                cast(
                    ColumnElement[object],
                    func.coalesce(DatasetModel.quality_score, -1).asc(),
                ),
                cast(ColumnElement[object], DatasetModel.id.asc()),
            ),
            "title_asc": (
                cast(ColumnElement[object], DatasetModel.title.asc()),
                cast(ColumnElement[object], DatasetModel.id.asc()),
            ),
            "title_desc": (
                cast(ColumnElement[object], DatasetModel.title.desc()),
                cast(ColumnElement[object], DatasetModel.id.asc()),
            ),
        }
        return sort_map.get(sort, sort_map["modified_desc"])

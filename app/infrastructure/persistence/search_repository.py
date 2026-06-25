"""Adapter SQLAlchemy pour recherche et detail dataset.

Implemente les ports SearchRepositoryPort et DatasetDetailRepositoryPort
en interrogeant le cache SQLite et en normalisant les reponses.
"""

from __future__ import annotations

from collections import Counter
from typing import cast

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.sql.elements import ColumnElement

from app.domain.query_expansion import expand_query
from app.domain.ranking import compute_hybrid_score
from app.infrastructure.persistence.database import SessionLocal
from app.infrastructure.persistence.models import DatasetModel, OrganizationModel, ResourceModel
from app.presentation.api.v1.schemas import (
    AccessMode,
    CompareItem,
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
            query_terms = self._parse_query_terms(query) if query else []

            # Expand query with multilingual synonyms (PDS-41)
            # Builds a LIKE clause that matches ALL expanded terms against
            # title, description, org name, and tags.
            expansion = expand_query(query) if query else None

            # Construire la clause WHERE
            base_filters: list[ColumnElement[bool]] = []
            if query and expansion and expansion.all_terms:
                # Construire un LIKE pour chaque terme etendu (OR logique)
                term_clauses: list[ColumnElement[bool]] = []
                for term in expansion.all_terms:
                    search_term = f"%{term}%"
                    term_clauses.append(
                        or_(
                            DatasetModel.title.collate("NOCASE").like(search_term),
                            DatasetModel.description.collate("NOCASE").like(search_term),
                            OrganizationModel.name.collate("NOCASE").like(search_term),
                            DatasetModel.tags.collate("NOCASE").like(search_term),
                        )
                    )
                base_filters.append(or_(*term_clauses))
            elif query:
                # Fallback: requete sans expansion (aucun concept reconnu)
                search_term = f"%{query.lower()}%"
                base_filters.append(
                    or_(
                        DatasetModel.title.collate("NOCASE").like(search_term),
                        DatasetModel.description.collate("NOCASE").like(search_term),
                        OrganizationModel.name.collate("NOCASE").like(search_term),
                        DatasetModel.tags.collate("NOCASE").like(search_term),
                    )
                )
            if org_filter:
                base_filters.append(DatasetModel.org_id == org_filter)
            if tag_filter:
                # Filtrer par tag exact: chercher le tag dans la liste (format JSON ou CSV)
                tag_term = f"%{tag_filter}%"
                base_filters.append(DatasetModel.tags.collate("NOCASE").like(tag_term))

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
            total_query = select(func.count()).select_from(DatasetModel).join(OrganizationModel)
            if where_clause is not None:
                total_query = total_query.where(where_clause)
            total = session.scalar(total_query) or 0

            # Chercher les datasets (sans pagination si tri hybride, on trie en Python)
            use_hybrid = sort == "hybrid" and bool(query_terms)
            if use_hybrid:
                # Pour le tri hybride, on charge tous les resultats filtres
                dataset_query = (
                    select(DatasetModel)
                    .join(OrganizationModel)
                    .order_by(cast(ColumnElement[object], DatasetModel.id.asc()))
                )
            else:
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

            # Construire les items de recherche avec signaux de ranking
            search_items: list[SearchDatasetItem] = []
            for ds in datasets:
                # Parser les tags depuis la chaine JSON-like
                tags = self._parse_tags(ds.tags) if ds.tags else []

                # Compter les ressources avec le bon format (si filtre)
                resource_count = len(ds.resources)
                resource_formats = list(
                    {r.format for r in ds.resources if r.format and r.format.upper()}
                )

                # Calculer les signaux de ranking hybride si requete presente
                ranking_signals = None
                if query_terms:
                    signals = compute_hybrid_score(
                        quality_score=ds.quality_score,
                        freshness_days=ds.freshness_days,
                        query_terms=query_terms,
                        title=ds.title,
                        description=ds.description,
                    )
                    ranking_signals = signals.to_dict()

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
                        ranking_signals=ranking_signals,
                    )
                )

            # Si tri hybride : trier par hybrid_score descendant puis paginer
            if use_hybrid:
                search_items.sort(
                    key=lambda item: (
                        item.ranking_signals["hybrid_score"] if item.ranking_signals else 0
                    ),
                    reverse=True,
                )
                search_items = search_items[offset : offset + limit]

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

    # --- Comparaison guidee (PDS-43) ---

    def get_by_ids(self, ids: list[str]) -> list[CompareItem]:
        """Charge plusieurs datasets en 1 seul round-trip DB pour comparaison.

        Optimisation batch : WHERE id IN (...) avec 3 JOINs au lieu de
        N requetes individuelles. Les IDs inexistants sont ignores.
        """
        if not ids:
            return []

        with SessionLocal() as session:
            datasets: list[DatasetModel] = list(
                session.scalars(
                    select(DatasetModel)
                    .options(
                        # Charger organisation et ressources en 1 seul round-trip
                        # (evite N+1 requetes pour 2-4 datasets).
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

            # Construire les items comparables dans l'ordre des IDs demandes
            ds_map: dict[str, DatasetModel] = {ds.id: ds for ds in datasets}
            items: list[CompareItem] = []
            for ds_id in ids:
                ds = ds_map.get(ds_id)
                if ds is None:
                    continue  # Silencieusement ignorer les IDs inexistants
                tags = self._parse_tags(ds.tags) if ds.tags else []
                resource_formats = list(
                    {r.format for r in ds.resources if r.format and r.format.upper()}
                )
                items.append(
                    CompareItem(
                        id=ds.id,
                        title=ds.title,
                        org_name=ds.organization.name if ds.organization else None,
                        description=ds.description,
                        license=None,  # Pas de metadata licence pour MVP
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

    # Helpers prive

    @staticmethod
    def _parse_query_terms(query: str | None) -> list[str]:
        """Decoupe une requete texte en termes normalises."""
        if not query or not query.strip():
            return []
        return [term.lower().strip() for term in query.split() if term.strip()]

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
            .join(OrganizationModel, OrganizationModel.id == DatasetModel.org_id)
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
        tag_query = select(DatasetModel.tags).select_from(DatasetModel).join(OrganizationModel)
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

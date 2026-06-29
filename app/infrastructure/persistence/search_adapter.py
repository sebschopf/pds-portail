"""Adapter SQLAlchemy pour la recherche full-text (FTS5).

Implemente SearchRepositoryPort avec index FTS5 optimise (PDS-94, PDS-95).
Utilise une sous-requete WHERE rowid IN (SELECT rowid FROM datasets_fts)
pour le filtrage, et ORDER BY bm25() via sous-requete scalaire pour le
tri hybride au lieu d'un chargement integral en RAM suivi d'un tri Python.

Contient egalement l'agregation des facettes (PDS-44) car elle est
intrinsequement liee a la recherche et n'est utilisee par aucun autre
adapter. ADR-003 (SRP) : cet adapter fait la recherche + ses facettes,
pas le detail ni la comparaison.
"""

from __future__ import annotations

from collections import Counter
from typing import cast

from sqlalchemy import and_, func, select, text
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement, TextClause

from app.domain.ranking import compute_hybrid_score
from app.infrastructure.persistence._search_helpers import parse_tags
from app.infrastructure.persistence.database import SessionLocal
from app.infrastructure.persistence.models import (
    DatasetModel,
    FacetsCacheModel,
    OrganizationModel,
    ResourceModel,
)
from app.presentation.api.v1.schemas import (
    FacetItem,
    SearchDatasetItem,
    SearchFacets,
    SearchResponse,
)

ORGANIZATION_FACET_LIMIT = 20


class SqlAlchemySearchAdapter:
    """Recherche full-text avec FTS5 optimise (BM25 natif pour le tri)."""

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

        Utilise l'index FTS5 pour une recherche full-text quasi instantanee
        sur 16K+ datasets. Le score BM25 natif de FTS5 est exploite pour
        le tri hybride via une sous-requete scalaire dans ORDER BY.
        """
        with SessionLocal() as session:
            query_terms = _parse_query_terms(query)
            query_str: str | None = query.strip() if query and query.strip() else None

            # Construire la sous-requete FTS5 (WHERE rowid IN ...)
            fts_where_clause: TextClause | None = None
            if query_str is not None:
                fts_where_clause = _search_fts_match(query_str)

            # Filtres non-FTS
            base_filters: list[ColumnElement[bool]] = []
            if org_filter:
                base_filters.append(DatasetModel.org_id == org_filter)
            if tag_filter:
                tag_term = f"%{tag_filter}%"
                base_filters.append(DatasetModel.tags.collate("NOCASE").like(tag_term))

            filters = list(base_filters)
            fmt_filter: str | None = format_filter

            # Compter les resultats totaux (avec FTS5 si recherche)
            total = self._count_total(session, fts_where_clause, fmt_filter, filters)

            # Determiner le tri
            use_hybrid = sort == "hybrid" and bool(query_terms)

            # Construire la query datasets
            dataset_query = select(DatasetModel).join(OrganizationModel)

            # Filtre FTS5 via sous-requete IN
            if fts_where_clause is not None:
                dataset_query = dataset_query.where(fts_where_clause)

            # Filtre format
            if fmt_filter is not None:
                dataset_query = dataset_query.join(
                    ResourceModel, ResourceModel.dataset_id == DatasetModel.id
                )
                dataset_query = dataset_query.where(
                    func.upper(ResourceModel.format) == fmt_filter.upper()
                )

            # Filtres non-FTS
            if filters:
                dataset_query = dataset_query.where(and_(*filters))

            # Tri et pagination
            if use_hybrid:
                # PDS-95 : tri BM25 natif via sous-requete scalaire
                # (quasi gratuit via l'index FTS5) au lieu de charger
                # tous les resultats en RAM pour un tri Python.
                dataset_query = dataset_query.order_by(
                    text(
                        "(SELECT bm25(datasets_fts) FROM datasets_fts "
                        "WHERE datasets_fts.rowid = datasets.ROWID) ASC"
                    )
                )
            else:
                dataset_query = dataset_query.order_by(*_order_by_for_sort(sort))

            dataset_query = dataset_query.offset(offset).limit(limit)

            datasets: list[DatasetModel] = list(session.scalars(dataset_query).all())

            # Construire les items de recherche avec signaux de ranking
            search_items: list[SearchDatasetItem] = []
            for ds in datasets:
                tags = parse_tags(ds.tags)
                resource_count = len(ds.resources)
                resource_formats = list(
                    {r.format for r in ds.resources if r.format and r.format.upper()}
                )

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

            # Le tri hybride est deja fait en SQL par bm25(), pas besoin
            # de trier en Python. On garde compute_hybrid_score uniquement
            # pour l'affichage des signaux de ranking.

            # Agreger les facettes
            facets = _aggregate_facets(session, base_filters, fmt_filter)

            return SearchResponse(
                total=total,
                offset=offset,
                limit=limit,
                datasets=search_items,
                facets=facets,
            )

    @staticmethod
    def _count_total(
        session: Session,
        fts_where_clause: TextClause | None,
        fmt_filter: str | None,
        filters: list[ColumnElement[bool]],
    ) -> int:
        """Compte les datasets correspondant aux filtres + FTS5."""
        count_query = (
            select(func.count(func.distinct(DatasetModel.id)))
            .select_from(DatasetModel)
            .join(OrganizationModel)
        )
        if fts_where_clause is not None:
            count_query = count_query.where(fts_where_clause)
        if fmt_filter is not None:
            count_query = count_query.join(
                ResourceModel, ResourceModel.dataset_id == DatasetModel.id
            )
            count_query = count_query.where(func.upper(ResourceModel.format) == fmt_filter.upper())
        if filters:
            count_query = count_query.where(and_(*filters))
        return session.scalar(count_query) or 0


# --- Helpers prives de recherche ---


def _parse_query_terms(query: str | None) -> list[str]:
    """Decoupe une requete texte en termes normalises (minuscules, sans vide)."""
    if not query or not query.strip():
        return []
    return [term.lower().strip() for term in query.split() if term.strip()]


def _search_fts_match(query: str) -> TextClause:
    """Construit une clause FTS5 via sous-requete IN (PDS-94, PDS-95).

    La table virtuelle datasets_fts n'est pas mappable en ORM SQLAlchemy,
    donc on utilise une sous-requete WHERE rowid IN (SELECT rowid FROM
    datasets_fts WHERE MATCH ...) qui reste quasi instantanee grace a
    l'index FTS5.

    Chaque terme est wrappe dans des guillemets pour un match exact
    du token, avec echappement des caracteres speciaux FTS5.
    """
    terms = [t.strip() for t in query.split() if t.strip()]
    if not terms:
        return text("1")
    escaped = [_escape_fts5_term(t) for t in terms]
    fts_query = " ".join(f'"{t}"' for t in escaped)
    return text(
        "datasets.ROWID IN ("
        "SELECT rowid FROM datasets_fts "
        f"WHERE datasets_fts MATCH '{fts_query}'"
        ")"
    )


def _escape_fts5_term(term: str) -> str:
    """Echappe les caracteres speciaux de la syntaxe FTS5."""
    return term.replace('"', '""')


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


# --- Agregation de facettes (PDS-44) ---


def _aggregate_facets(
    session: Session,
    base_filters: list[ColumnElement[bool]],
    format_filter: str | None = None,
) -> SearchFacets:
    """Lit les facettes depuis le cache pre-calcule, avec fallback direct (PDS-44).

    Si la table facets_cache est peuplee et qu'aucun filtre n'est actif,
    les facettes sont lues directement sans agregation SQL couteuse.
    Des qu'un filtre (base_filters ou format_filter) est actif, on utilise
    l'agregation directe pour garantir des compteurs coherents avec les filtres.
    """
    has_active_filters = bool(base_filters) or format_filter is not None
    cache_count = session.query(FacetsCacheModel).count()

    if cache_count > 0 and not has_active_filters:
        # Cache hit : lecture directe (pas de filtres actifs)
        cached_org_rows = (
            session.query(FacetsCacheModel)
            .filter(FacetsCacheModel.facet_type == "org")
            .order_by(FacetsCacheModel.count.desc())
            .all()
        )
        cached_orgs = [
            FacetItem(name=row.name, display_name=row.display_name, count=row.count)
            for row in cached_org_rows
        ]
        cached_fmt_rows = (
            session.query(FacetsCacheModel)
            .filter(FacetsCacheModel.facet_type == "format")
            .order_by(FacetsCacheModel.count.desc())
            .all()
        )
        cached_formats = [FacetItem(name=row.name, count=row.count) for row in cached_fmt_rows]

        cached_tags = __aggregate_tags(session, base_filters)
        return SearchFacets(organizations=cached_orgs, formats=cached_formats, tags=cached_tags)

    # Fallback : agregation directe (cache vide ou filtres actifs)
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
        .limit(ORGANIZATION_FACET_LIMIT)
    )
    if format_filter is not None:
        org_query = org_query.join(ResourceModel, ResourceModel.dataset_id == DatasetModel.id)
        org_query = org_query.where(func.upper(ResourceModel.format) == format_filter.upper())
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
        if format_name:
            formats.append(FacetItem(name=str(format_name), count=int(count)))

    tags = __aggregate_tags_with_format(session, base_filters, format_filter)

    return SearchFacets(organizations=orgs, formats=formats, tags=tags)


def __aggregate_tags(
    session: Session,
    base_filters: list[ColumnElement[bool]],
) -> list[FacetItem]:
    """Agrege les tags depuis les datasets (toujours depuis la DB, pas en cache)."""
    return __aggregate_tags_with_format(session, base_filters, format_filter=None)


def __aggregate_tags_with_format(
    session: Session,
    base_filters: list[ColumnElement[bool]],
    format_filter: str | None,
) -> list[FacetItem]:
    """Agrege les tags depuis les datasets, avec filtre format optionnel."""
    tag_query = select(DatasetModel.tags).select_from(DatasetModel).join(OrganizationModel)
    if format_filter is not None:
        tag_query = tag_query.join(ResourceModel, ResourceModel.dataset_id == DatasetModel.id)
        tag_query = tag_query.where(func.upper(ResourceModel.format) == format_filter.upper())
    if base_filters:
        tag_query = tag_query.where(and_(*base_filters))
    tag_counter: Counter[str] = Counter()
    for tags_str in session.scalars(tag_query).all():
        if not tags_str:
            continue
        for tag in parse_tags(tags_str):
            if tag:
                tag_counter[tag] += 1
    return [FacetItem(name=name, count=count) for name, count in tag_counter.most_common()]

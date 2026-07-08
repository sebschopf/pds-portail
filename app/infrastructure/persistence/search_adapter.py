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

import logging
from typing import cast

from sqlalchemy import and_, func, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement, TextClause

from app.domain.ranking import compute_hybrid_score
from app.infrastructure.persistence._search_helpers import parse_tags
from app.infrastructure.persistence.database import SessionLocal
from app.infrastructure.persistence.models import (
    DatasetModel,
    OrganizationModel,
    ResourceModel,
)
from app.infrastructure.persistence.search_facets import aggregate_facets as _aggregate_facets
from app.infrastructure.persistence.search_fts import (
    build_fts_match_any_terms_clause as _search_fts_match_any_terms,
)
from app.infrastructure.persistence.search_fts import build_fts_match_clause as _search_fts_match
from app.infrastructure.persistence.search_fts import (
    is_fts5_operational_error as _is_fts5_operational_error,
)
from app.infrastructure.persistence.search_tag_filter import (
    build_exact_tag_filter as _build_exact_tag_filter,
)
from app.presentation.api.v1.schemas import (
    RankingSignals,
    SearchDatasetItem,
    SearchResponse,
)

logger = logging.getLogger(__name__)


class SqlAlchemySearchAdapter:
    """Recherche full-text avec FTS5 optimise (BM25 natif pour le tri)."""

    def search(
        self,
        query: str | None = None,
        expanded_terms: list[str] | None = None,
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
        query_terms = _parse_query_terms(query)
        query_str: str | None = query.strip() if query and query.strip() else None

        # Construire la sous-requete FTS5 (WHERE rowid IN ...)
        fts_where_clause: TextClause | None = None
        if query_str is not None:
            if expanded_terms:
                original_terms = [t.strip() for t in query_str.split() if t.strip()]
                all_terms = original_terms + [t for t in expanded_terms if t.strip()]
                fts_where_clause = _search_fts_match_any_terms(all_terms)
            else:
                fts_where_clause = _search_fts_match(query_str)

        # Filtres non-FTS
        base_filters: list[ColumnElement[bool]] = []
        if org_filter:
            base_filters.append(DatasetModel.org_id == org_filter)
        if tag_filter:
            base_filters.append(_build_exact_tag_filter(tag_filter))

        filters = list(base_filters)
        fmt_filter: str | None = format_filter

        with SessionLocal() as session:
            try:
                return self._run_query(
                    session=session,
                    query_terms=query_terms,
                    offset=offset,
                    limit=limit,
                    sort=sort,
                    fts_where_clause=fts_where_clause,
                    base_filters=base_filters,
                    filters=filters,
                    fmt_filter=fmt_filter,
                )
            except OperationalError as exc:
                if not _is_fts5_operational_error(exc):
                    raise

                logger.warning(
                    "FTS5 indisponible ou requete MATCH invalide: fallback SQL sans FTS5",
                    exc_info=True,
                )

                # Degradation controlee: pas de crash 500, on conserve les filtres non-FTS
                # et un tri deterministe sans bm25.
                return self._run_query(
                    session=session,
                    query_terms=query_terms,
                    offset=offset,
                    limit=limit,
                    sort=sort,
                    fts_where_clause=None,
                    base_filters=base_filters,
                    filters=filters,
                    fmt_filter=fmt_filter,
                )

    def _run_query(
        self,
        session: Session,
        query_terms: list[str],
        offset: int,
        limit: int,
        sort: str,
        fts_where_clause: TextClause | None,
        base_filters: list[ColumnElement[bool]],
        filters: list[ColumnElement[bool]],
        fmt_filter: str | None,
    ) -> SearchResponse:
        # Compter les resultats totaux (avec FTS5 si recherche)
        total = self._count_total(session, fts_where_clause, fmt_filter, filters)

        # Le tri hybride (bm25) n'est possible que si FTS5 est actif.
        use_hybrid = sort == "hybrid" and bool(query_terms) and fts_where_clause is not None

        # Construire la query datasets
        dataset_query = select(DatasetModel).join(OrganizationModel)

        # Filtre FTS5 via sous-requete IN
        if fts_where_clause is not None:
            dataset_query = dataset_query.where(fts_where_clause)

        # Filtre format par sous-requête EXISTS pour éviter les doublons
        # quand un dataset a plusieurs ressources du même format (ex: API).
        if fmt_filter is not None:
            dataset_query = dataset_query.where(
                DatasetModel.resources.any(func.upper(ResourceModel.format) == fmt_filter.upper())
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
                ranking_signals = RankingSignals(
                    hybrid_score=round(signals.hybrid_score, 4),
                    text_score=round(signals.text_score, 4),
                    quality_normalized=round(signals.quality_normalized, 4),
                    freshness_component=round(signals.freshness_component, 4),
                    weight_text=signals.weight_text,
                    weight_quality=signals.weight_quality,
                    weight_freshness=signals.weight_freshness,
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
                    ranking_signals=ranking_signals,
                )
            )

        # Le tri hybride est deja fait en SQL par bm25(), pas besoin
        # de trier en Python. On garde compute_hybrid_score uniquement
        # pour l'affichage des signaux de ranking.

        # Agreger les facettes
        facets = _aggregate_facets(session, base_filters, fmt_filter, fts_where_clause)

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

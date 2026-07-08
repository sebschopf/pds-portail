"""Agregation des facettes dediee a la recherche."""

from __future__ import annotations

from collections import Counter
from typing import cast

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement, TextClause

from app.infrastructure.persistence._search_helpers import parse_tags
from app.infrastructure.persistence.models import (
    DatasetModel,
    FacetsCacheModel,
    OrganizationModel,
    ResourceModel,
)
from app.presentation.api.v1.schemas import FacetItem, SearchFacets

ORGANIZATION_FACET_LIMIT = 20


def aggregate_facets(
    session: Session,
    base_filters: list[ColumnElement[bool]],
    format_filter: str | None = None,
    fts_where_clause: TextClause | None = None,
) -> SearchFacets:
    """Lit les facettes depuis le cache pre-calcule, avec fallback direct."""
    has_active_filters = (
        bool(base_filters) or format_filter is not None or fts_where_clause is not None
    )
    cache_count = session.query(FacetsCacheModel).count()

    if cache_count > 0 and not has_active_filters:
        cached_org_rows = (
            session.query(FacetsCacheModel)
            .filter(FacetsCacheModel.facet_type == "org")
            .order_by(FacetsCacheModel.count.desc())
            .all()
        )
        cached_orgs = _deduplicate_facets_by_name(
            [
                FacetItem(
                    name=str(row.name),
                    display_name=str(row.display_name) if row.display_name is not None else None,
                    count=int(row.count),
                )
                for row in cached_org_rows
            ]
        )

        cached_fmt_rows = (
            session.query(FacetsCacheModel)
            .filter(FacetsCacheModel.facet_type == "format")
            .order_by(FacetsCacheModel.count.desc())
            .all()
        )
        cached_formats = _deduplicate_facets_by_name(
            [FacetItem(name=str(row.name), count=int(row.count)) for row in cached_fmt_rows]
        )

        cached_tags = _aggregate_tags(session, base_filters, fts_where_clause)
        return SearchFacets(organizations=cached_orgs, formats=cached_formats, tags=cached_tags)

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
    if fts_where_clause is not None:
        org_query = org_query.where(fts_where_clause)
    if base_filters:
        org_query = org_query.where(and_(*base_filters))

    org_rows = cast(list[tuple[str, str, int]], session.execute(org_query).all())
    orgs_raw: list[FacetItem] = []
    for org_id, org_name, count in org_rows:
        orgs_raw.append(
            FacetItem(
                name=org_id,
                display_name=org_name,
                count=count,
            )
        )
    orgs = _deduplicate_facets_by_name(orgs_raw)

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
    if fts_where_clause is not None:
        format_query = format_query.where(fts_where_clause)
    if base_filters:
        format_query = format_query.where(and_(*base_filters))

    format_rows = cast(list[tuple[str | None, int]], session.execute(format_query).all())
    formats_raw: list[FacetItem] = []
    for format_name, count in format_rows:
        if format_name:
            formats_raw.append(FacetItem(name=format_name, count=count))
    formats = _deduplicate_facets_by_name(formats_raw)

    tags = _aggregate_tags_with_format(session, base_filters, format_filter, fts_where_clause)

    return SearchFacets(organizations=orgs, formats=formats, tags=tags)


def _aggregate_tags(
    session: Session,
    base_filters: list[ColumnElement[bool]],
    fts_where_clause: TextClause | None,
) -> list[FacetItem]:
    """Agrege les tags depuis les datasets (toujours depuis la DB, pas en cache)."""
    return _aggregate_tags_with_format(
        session,
        base_filters,
        format_filter=None,
        fts_where_clause=fts_where_clause,
    )


def _aggregate_tags_with_format(
    session: Session,
    base_filters: list[ColumnElement[bool]],
    format_filter: str | None,
    fts_where_clause: TextClause | None,
) -> list[FacetItem]:
    """Agrege les tags depuis les datasets, avec filtre format optionnel."""
    tag_query = select(DatasetModel.tags).select_from(DatasetModel).join(OrganizationModel)
    if format_filter is not None:
        tag_query = tag_query.join(ResourceModel, ResourceModel.dataset_id == DatasetModel.id)
        tag_query = tag_query.where(func.upper(ResourceModel.format) == format_filter.upper())
    if fts_where_clause is not None:
        tag_query = tag_query.where(fts_where_clause)
    if base_filters:
        tag_query = tag_query.where(and_(*base_filters))

    tag_counter: Counter[str] = Counter()
    tags_values = cast(list[str | None], session.scalars(tag_query).all())
    for tags_str in tags_values:
        if not tags_str:
            continue
        for tag in parse_tags(tags_str):
            if tag:
                tag_counter[tag] += 1
    return _deduplicate_facets_by_name(
        [FacetItem(name=name, count=count) for name, count in tag_counter.most_common()]
    )


def _deduplicate_facets_by_name(facets: list[FacetItem]) -> list[FacetItem]:
    """Dédoublonne les facettes par nom (première occurrence gagnante)."""
    seen: set[str] = set()
    deduped: list[FacetItem] = []
    for facet in facets:
        if facet.name in seen:
            continue
        seen.add(facet.name)
        deduped.append(facet)
    return deduped

"""Regles de calcul des indicateurs qualite dataset.

Les formules sont explicites et stables pour le MVP, avec un score final sur 100
compose de 5 dimensions ponderees a 20 points chacune.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

_STANDARD_FORMATS = {"csv", "json", "geojson", "api"}
_PROPRIETARY_FORMATS = {"xls", "xlsx", "shp"}
_GEO_TAG_KEYWORDS = {
    "geo",
    "geospatial",
    "spatial",
    "carto",
    "map",
    "geographie",
    "territoire",
}


@dataclass(frozen=True, slots=True)
class DatasetIndicatorInput:
    """Entree minimale necessaire au calcul des indicateurs qualite."""

    description: str | None
    tags: list[str]
    created: str | None
    modified: str | None
    resource_formats: list[str]
    resource_count: int


@dataclass(frozen=True, slots=True)
class DatasetIndicators:
    """Indicateurs normalises exposes au reste du backend."""

    quality_score: int
    completeness: int
    freshness_days: int | None


def compute_indicators(
    input_data: DatasetIndicatorInput, now: datetime | None = None
) -> DatasetIndicators:
    """Calcule les indicateurs de base selon la formule ponderee SPEC-001."""

    reference_now = now if now is not None else datetime.now(UTC)
    freshness_days = compute_freshness_days(
        input_data.modified or input_data.created, reference_now
    )
    completeness = compute_completeness(input_data)

    meta_complete_component = _meta_complete_component(completeness)
    fresh_component = _fresh_component(freshness_days)
    format_component = _format_standard_component(input_data.resource_formats)
    geo_temporal_component = _geo_temporal_component(
        input_data.tags, input_data.created, input_data.modified
    )
    resource_count_component = _resource_count_component(input_data.resource_count)

    weighted_score = 20 * (
        meta_complete_component
        + fresh_component
        + format_component
        + geo_temporal_component
        + resource_count_component
    )

    return DatasetIndicators(
        quality_score=int(round(weighted_score)),
        completeness=completeness,
        freshness_days=freshness_days,
    )


def compute_completeness(input_data: DatasetIndicatorInput) -> int:
    """Calcule la completude (0-100) sur 5 champs metadata stables."""

    checks = [
        bool(input_data.description and input_data.description.strip()),
        bool(input_data.tags),
        bool(input_data.created),
        bool(input_data.modified),
        input_data.resource_count > 0,
    ]
    return int(round((sum(1 for check in checks if check) / len(checks)) * 100))


def compute_freshness_days(
    modified_or_created: str | None, now: datetime | None = None
) -> int | None:
    """Calcule le nombre de jours depuis la derniere date metadata exploitable."""

    if not modified_or_created:
        return None

    parsed_dt = _parse_iso_datetime(modified_or_created)
    if parsed_dt is None:
        return None

    reference_now = now if now is not None else datetime.now(UTC)
    if reference_now.tzinfo is None:
        reference_now = reference_now.replace(tzinfo=UTC)

    delta_days = (reference_now - parsed_dt).days
    return max(0, delta_days)


def _meta_complete_component(completeness: int) -> float:
    if completeness >= 80:
        return 1.0
    if completeness >= 40:
        return 0.5
    return 0.0


def _fresh_component(freshness_days: int | None) -> float:
    if freshness_days is None:
        return 0.0
    if freshness_days <= 30:
        return 1.0
    if freshness_days <= 180:
        return 0.5
    return 0.0


def _format_standard_component(resource_formats: list[str]) -> float:
    if not resource_formats:
        return 0.0

    normalized_formats = {
        format_name.strip().lower() for format_name in resource_formats if format_name.strip()
    }
    if not normalized_formats:
        return 0.0
    if normalized_formats.intersection(_STANDARD_FORMATS):
        return 1.0
    if normalized_formats.issubset(_PROPRIETARY_FORMATS):
        return 0.5
    return 0.0


def _geo_temporal_component(tags: list[str], created: str | None, modified: str | None) -> float:
    has_geo_signal = any(_is_geo_tag(tag) for tag in tags)
    has_temporal_signal = bool(created or modified)

    if has_geo_signal and has_temporal_signal:
        return 1.0
    if has_geo_signal or has_temporal_signal:
        return 0.5
    return 0.0


def _resource_count_component(resource_count: int) -> float:
    if resource_count >= 3:
        return 1.0
    if resource_count >= 1:
        return 0.5
    return 0.0


def _is_geo_tag(tag: str) -> bool:
    normalized_tag = tag.strip().lower()
    return any(keyword in normalized_tag for keyword in _GEO_TAG_KEYWORDS)


def _parse_iso_datetime(value: str) -> datetime | None:
    normalized_value = value.strip()
    if not normalized_value:
        return None

    if normalized_value.endswith("Z"):
        normalized_value = normalized_value[:-1] + "+00:00"

    try:
        parsed_dt = datetime.fromisoformat(normalized_value)
    except ValueError:
        return None

    if parsed_dt.tzinfo is None:
        return parsed_dt.replace(tzinfo=UTC)
    return parsed_dt.astimezone(UTC)

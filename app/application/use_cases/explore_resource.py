"""Exploration structurée d'une ressource CSV ou JSON (PDS-82).

Le cas d'usage s'appuie sur le détail ressource existant, parse le contenu
source avec la stdlib, puis met en cache le résultat sérialisé pendant 24h.
"""

from __future__ import annotations

import csv
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from io import StringIO
from statistics import mean, median
from urllib.request import urlopen

from fastapi import HTTPException

from app.application.ports.query_cache_repository import QueryCacheRepositoryPort
from app.domain.cache_invalidation import CacheEndpointType, build_explore_cache_key
from app.presentation.api.v1.schemas import (
    ColumnInfo as ColumnInfoSchema,
)
from app.presentation.api.v1.schemas import (
    ColumnStats as ColumnStatsSchema,
)
from app.presentation.api.v1.schemas import (
    ExploreResourceResponse,
    ResourceDetailResponse,
)

logger = logging.getLogger(__name__)

MAX_RESOURCE_BYTES = 50 * 1024 * 1024
FETCH_CHUNK_SIZE = 64 * 1024

_INTEGER_PATTERN = re.compile(r"^[+-]?\d+$")
_FLOAT_PATTERN = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")


@dataclass(slots=True)
class ColumnStats:
    """Statistiques descriptives pour une colonne numerique."""

    min: float | None = None
    max: float | None = None
    mean: float | None = None
    median: float | None = None


@dataclass(slots=True)
class ColumnInfo:
    """Colonne detectee dans une ressource exploree."""

    name: str
    detected_type: str
    fill_rate: float
    sample_values: list[str] = field(default_factory=list)
    stats: ColumnStats | None = None


@dataclass(slots=True)
class ExploredResource:
    """Resultat normalise d'une exploration de ressource."""

    resource_id: str
    format: str
    parsed_at: str
    columns: list[ColumnInfo]
    row_count: int
    cached: bool = False

    def to_response_model(self) -> ExploreResourceResponse:
        """Convertit le resultat domaine vers le schema API."""

        return ExploreResourceResponse(
            resource_id=self.resource_id,
            format=self.format,
            parsed_at=self.parsed_at,
            columns=[_column_to_schema(column) for column in self.columns],
            row_count=self.row_count,
            cached=self.cached,
        )


def explore_resource(
    detail: ResourceDetailResponse,
    cache: QueryCacheRepositoryPort,
    ttl_seconds: int,
    fetch_timeout_seconds: float = 15.0,
) -> ExploreResourceResponse:
    """Retourne l'exploration d'une ressource en utilisant un cache 24h."""

    cache_key = build_explore_cache_key(detail.id)
    cached = cache.get(cache_key, ttl_seconds)
    if cached is not None:
        return _load_cached_response(cached)

    if not detail.url:
        raise HTTPException(status_code=422, detail="Resource URL is missing")

    parsed_at = datetime.now(UTC).isoformat()
    raw_content = _fetch_resource_content(detail.url, fetch_timeout_seconds)
    try:
        explored = _parse_resource_content(
            resource_id=detail.id,
            resource_format=detail.format or "",
            content=raw_content,
            parsed_at=parsed_at,
        )
    except (csv.Error, json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        logger.warning("Parsing failed for resource %s: %s", detail.id, exc)
        raise HTTPException(
            status_code=422, detail=f"Failed to parse resource {detail.id}"
        ) from exc

    response = explored.to_response_model()
    cache.set(cache_key, CacheEndpointType.EXPLORATION, response.model_dump_json())
    return response


def _load_cached_response(cached_json: str) -> ExploreResourceResponse:
    data = json.loads(cached_json)
    response = ExploreResourceResponse(**data)
    return response.model_copy(update={"cached": True})


def _fetch_resource_content(url: str, timeout_seconds: float) -> str:
    with urlopen(url, timeout=timeout_seconds) as response:
        payload = bytearray()
        while True:
            chunk = response.read(FETCH_CHUNK_SIZE)
            if not chunk:
                break
            payload.extend(chunk)
            if len(payload) > MAX_RESOURCE_BYTES:
                raise HTTPException(status_code=422, detail="Resource exceeds 50 MB limit")
    return bytes(payload).decode("utf-8-sig")


def _parse_resource_content(
    resource_id: str,
    resource_format: str,
    content: str,
    parsed_at: str,
) -> ExploredResource:
    format_lower = resource_format.lower()
    if format_lower == "csv":
        return _parse_csv(resource_id, content, parsed_at)
    if format_lower == "json":
        return _parse_json(resource_id, content, parsed_at)
    raise HTTPException(status_code=422, detail=f"Format '{resource_format}' not supported")


def _parse_csv(resource_id: str, content: str, parsed_at: str) -> ExploredResource:
    reader = csv.DictReader(StringIO(content))
    fieldnames = list(reader.fieldnames or [])
    rows = list(reader)
    return ExploredResource(
        resource_id=resource_id,
        format="csv",
        parsed_at=parsed_at,
        columns=_build_columns_from_rows(fieldnames, rows),
        row_count=len(rows),
    )


def _parse_json(resource_id: str, content: str, parsed_at: str) -> ExploredResource:
    payload = json.loads(content)

    if isinstance(payload, list):
        if payload and all(isinstance(row, dict) for row in payload):
            fieldnames = _ordered_union([list(row.keys()) for row in payload])
            rows = [dict(row) for row in payload]
            return ExploredResource(
                resource_id=resource_id,
                format="json",
                parsed_at=parsed_at,
                columns=_build_columns_from_rows(fieldnames, rows),
                row_count=len(rows),
            )

        values = [_stringify_value(item) for item in payload]
        return ExploredResource(
            resource_id=resource_id,
            format="json",
            parsed_at=parsed_at,
            columns=[_build_column("value", values, len(payload))],
            row_count=len(payload),
        )

    if isinstance(payload, dict):
        fieldnames = list(payload.keys())
        rows = [payload]
        return ExploredResource(
            resource_id=resource_id,
            format="json",
            parsed_at=parsed_at,
            columns=_build_columns_from_rows(fieldnames, rows),
            row_count=1,
        )

    values = [_stringify_value(payload)]
    return ExploredResource(
        resource_id=resource_id,
        format="json",
        parsed_at=parsed_at,
        columns=[_build_column("value", values, 1)],
        row_count=1,
    )


def _build_columns_from_rows(
    fieldnames: list[str], rows: list[dict[str, object]]
) -> list[ColumnInfo]:
    return [
        _build_column(fieldname, [_row_value(row.get(fieldname)) for row in rows], len(rows))
        for fieldname in fieldnames
    ]


def _build_column(name: str, values: list[str], row_count: int) -> ColumnInfo:
    non_empty_values = [value for value in values if value.strip()]
    detected_type = _detect_type(non_empty_values)
    stats = _build_stats(non_empty_values, detected_type)
    fill_rate = 0.0 if row_count == 0 else len(non_empty_values) / row_count
    return ColumnInfo(
        name=name,
        detected_type=detected_type,
        fill_rate=fill_rate,
        sample_values=non_empty_values[:5],
        stats=stats,
    )


def _detect_type(values: list[str]) -> str:
    if not values:
        return "unknown"
    if all(_is_integer(value) for value in values):
        return "integer"
    if all(_is_float(value) for value in values):
        return "float"
    if all(_is_iso_date(value) for value in values):
        return "date"
    return "string"


def _build_stats(values: list[str], detected_type: str) -> ColumnStats | None:
    if detected_type not in {"integer", "float"} or not values:
        return None

    numeric_values = [float(value) for value in values]
    return ColumnStats(
        min=min(numeric_values),
        max=max(numeric_values),
        mean=mean(numeric_values),
        median=median(numeric_values),
    )


def _is_integer(value: str) -> bool:
    return bool(_INTEGER_PATTERN.match(value.strip()))


def _is_float(value: str) -> bool:
    return bool(_FLOAT_PATTERN.match(value.strip()))


def _is_iso_date(value: str) -> bool:
    candidate = value.strip().replace("Z", "+00:00")
    try:
        datetime.fromisoformat(candidate)
    except ValueError:
        return False
    return True


def _row_value(value: object) -> str:
    if value is None:
        return ""
    return _stringify_value(value)


def _stringify_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return value.strip()
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _ordered_union(collections: list[list[str]]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for names in collections:
        for name in names:
            if name in seen:
                continue
            seen.add(name)
            ordered.append(name)
    return ordered


def _column_to_schema(column: ColumnInfo) -> ColumnInfoSchema:
    stats = None
    if column.stats is not None:
        stats = ColumnStatsSchema(
            min=column.stats.min,
            max=column.stats.max,
            mean=column.stats.mean,
            median=column.stats.median,
        )
    return ColumnInfoSchema(
        name=column.name,
        detected_type=column.detected_type,
        fill_rate=column.fill_rate,
        sample_values=column.sample_values,
        stats=stats,
    )

"""Exploration structurée d'une ressource CSV, JSON ou RDF (PDS-82).

Le cas d'usage s'appuie sur le détail ressource existant, parse le contenu
source avec la stdlib, puis met en cache le résultat sérialisé pendant 24h.
"""

from __future__ import annotations

import csv
import json
import logging
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from io import StringIO
from socket import timeout as SocketTimeout
from statistics import mean, median
from typing import cast
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from fastapi import HTTPException
from rdflib import Graph
from rdflib.namespace import RDF, RDFS, SKOS

from app.application.ports.query_cache_repository import QueryCacheRepositoryPort
from app.domain.cache_invalidation import CacheEndpointType, build_explore_cache_key
from app.domain.dataset_analyzer import Analysis, analyse_explored_resource
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
from app.presentation.api.v1.schemas import (
    ResourceAnalysis as ResourceAnalysisSchema,
)

logger = logging.getLogger(__name__)

MAX_RESOURCE_BYTES = 50 * 1024 * 1024
FETCH_CHUNK_SIZE = 64 * 1024

_INTEGER_PATTERN = re.compile(r"^[+-]?\d+$")
_FLOAT_PATTERN = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")


def _empty_str_list() -> list[str]:
    return []


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
    sample_values: list[str] = field(default_factory=_empty_str_list)
    stats: ColumnStats | None = None


@dataclass(slots=True)
class ExploredResource:
    """Resultat normalise d'une exploration de ressource."""

    resource_id: str
    format: str
    parsed_at: str
    columns: list[ColumnInfo]
    row_count: int
    analysis: Analysis | None = None
    cached: bool = False

    def to_response_model(self) -> ExploreResourceResponse:
        """Convertit le resultat domaine vers le schema API."""

        return ExploreResourceResponse(
            resource_id=self.resource_id,
            format=self.format,
            parsed_at=self.parsed_at,
            columns=[_column_to_schema(column) for column in self.columns],
            row_count=self.row_count,
            analysis=_analysis_to_schema(self.analysis),
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

    explored.analysis = analyse_explored_resource(explored, detail)

    response = explored.to_response_model()
    cache.set(cache_key, CacheEndpointType.EXPLORATION, response.model_dump_json())
    return response


def _load_cached_response(cached_json: str) -> ExploreResourceResponse:
    data = json.loads(cached_json)
    response = ExploreResourceResponse(**data)
    return response.model_copy(update={"cached": True})


def _fetch_resource_content(url: str, timeout_seconds: float) -> str:
    try:
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
    except HTTPError as exc:
        logger.warning("Failed to fetch resource URL %s: HTTP %s", url, exc.code)
        raise HTTPException(
            status_code=422,
            detail=f"Impossible de recuperer la ressource (HTTP {exc.code})",
        ) from exc
    except URLError as exc:
        if isinstance(exc.reason, TimeoutError | SocketTimeout):
            logger.warning("Timeout fetching resource URL %s", url)
            raise HTTPException(
                status_code=504,
                detail="Le telechargement de la ressource a expire (timeout)",
            ) from exc
        logger.warning("Resource URL unreachable %s: %s", url, exc.reason)
        raise HTTPException(status_code=422, detail="URL de ressource inaccessible") from exc
    except TimeoutError as exc:
        logger.warning("Timeout fetching resource URL %s", url)
        raise HTTPException(
            status_code=504,
            detail="Le telechargement de la ressource a expire (timeout)",
        ) from exc
    except UnicodeDecodeError as exc:
        logger.warning("Failed to decode resource URL %s as UTF-8", url)
        raise HTTPException(
            status_code=422,
            detail="Le contenu de la ressource n'est pas decodable en UTF-8",
        ) from exc


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
    if _is_rdf_format(format_lower):
        return _parse_rdf(resource_id, resource_format, content, parsed_at)
    raise HTTPException(status_code=422, detail=f"Format '{resource_format}' not supported")


def _is_rdf_format(format_lower: str) -> bool:
    return format_lower in {
        "rdf",
        "rdf/xml",
        "xml",
        "ttl",
        "turtle",
        "n3",
        "json-ld",
        "jsonld",
    }


def _parse_rdf(
    resource_id: str,
    resource_format: str,
    content: str,
    parsed_at: str,
) -> ExploredResource:
    graph = Graph()
    rdf_format = _map_rdf_format(resource_format)

    try:
        if rdf_format is not None:
            graph.parse(data=content, format=rdf_format)
        else:
            _parse_rdf_with_fallback_formats(graph, content)
    except Exception as exc:  # pragma: no cover - erreurs variees selon parser
        raise ValueError("Invalid RDF content") from exc

    rdf_type_values = [str(value) for value in graph.objects(None, RDF.type)]
    dominant_class = _most_frequent_value(rdf_type_values)
    classes_count = len(set(rdf_type_values))
    properties_count = len(set(str(predicate) for predicate in graph.predicates()))
    instances_count = len(set(str(subject) for subject in graph.subjects(RDF.type, None)))
    namespaces_count = len(list(graph.namespaces()))
    language_count = len(
        {
            language
            for language in (
                _extract_label_language(label) for label in graph.objects(None, RDFS.label)
            )
            if language
        }
    )
    has_hierarchy = int(
        any(True for _ in graph.triples((None, SKOS.broader, None)))
        or any(True for _ in graph.triples((None, SKOS.narrower, None)))
    )

    row: dict[str, str | int] = {
        "dominant_class": dominant_class,
        "classes_count": classes_count,
        "properties_count": properties_count,
        "instances_count": instances_count,
        "namespaces_count": namespaces_count,
        "language_count": language_count,
        "has_hierarchy": has_hierarchy,
    }
    fieldnames = list(row.keys())
    return ExploredResource(
        resource_id=resource_id,
        format=(resource_format or "rdf").lower(),
        parsed_at=parsed_at,
        columns=_build_columns_from_rows(fieldnames, [row]),
        row_count=len(graph),
    )


def _map_rdf_format(resource_format: str) -> str | None:
    normalized = resource_format.strip().lower()
    mapping = {
        "ttl": "turtle",
        "turtle": "turtle",
        "n3": "n3",
        "json-ld": "json-ld",
        "jsonld": "json-ld",
        "rdf/xml": "xml",
        "xml": "xml",
    }
    return mapping.get(normalized)


def _parse_rdf_with_fallback_formats(graph: Graph, content: str) -> None:
    formats_to_try = ["turtle", "xml", "n3", "json-ld"]
    last_error: Exception | None = None
    for candidate in formats_to_try:
        try:
            graph.parse(data=content, format=candidate)
            return
        except Exception as exc:  # pragma: no cover - erreurs parseur dependantes
            last_error = exc
    if last_error is not None:
        raise last_error


def _most_frequent_value(values: list[str]) -> str:
    if not values:
        return ""
    frequencies: dict[str, int] = {}
    for value in values:
        frequencies[value] = frequencies.get(value, 0) + 1
    best_value = max(frequencies.items(), key=lambda item: item[1])[0]
    return _local_name(best_value)


def _local_name(value: str) -> str:
    if "#" in value:
        return value.rsplit("#", 1)[-1]
    if "/" in value:
        return value.rsplit("/", 1)[-1]
    return value


def _extract_label_language(label: object) -> str:
    """Retourne le tag de langue RDF si disponible."""

    language = getattr(label, "language", None)
    return language if isinstance(language, str) else ""


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
    payload = cast(object, json.loads(content))

    if isinstance(payload, list):
        payload_items = cast(list[object], payload)

        if payload_items and all(isinstance(row, dict) for row in payload_items):
            dict_rows = [cast(dict[str, object], row) for row in payload_items]
            fieldnames = _ordered_union([list(row.keys()) for row in dict_rows])
            rows = [dict(row) for row in dict_rows]
            return ExploredResource(
                resource_id=resource_id,
                format="json",
                parsed_at=parsed_at,
                columns=_build_columns_from_rows(fieldnames, rows),
                row_count=len(rows),
            )

        values = [_stringify_value(item) for item in payload_items]
        return ExploredResource(
            resource_id=resource_id,
            format="json",
            parsed_at=parsed_at,
            columns=[_build_column("value", values, len(payload_items))],
            row_count=len(payload_items),
        )

    if isinstance(payload, dict):
        payload_map = cast(dict[str, object], payload)
        fieldnames = list(payload_map.keys())
        rows = [payload_map]
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
    fieldnames: Sequence[str], rows: Sequence[Mapping[str, object]]
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


def _analysis_to_schema(analysis: Analysis | None) -> ResourceAnalysisSchema | None:
    if analysis is None:
        return None
    return ResourceAnalysisSchema(
        summary=analysis.summary,
        capabilities=analysis.capabilities,
        caveats=analysis.caveats,
    )

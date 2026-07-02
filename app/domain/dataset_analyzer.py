"""Analyse heuristique d'une ressource exploree."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol

_SWISS_LOCALITY_NAMES = {
    "commune",
    "communes",
    "gemeinde",
    "gemeinden",
    "canton",
    "cantons",
    "ville",
    "city",
    "town",
    "municipality",
    "municipalite",
}
_TEMPORAL_NAMES = {"annee", "year", "jahr", "date", "datum", "timestamp", "mois", "month"}
_IDENTIFIER_NAMES = {"id", "uuid", "code", "code_postal", "npa", "zip", "identifier"}
_CATEGORICAL_NAMES = {"type", "categorie", "category", "statut", "status", "mode", "genre"}

_YEAR_PATTERN = re.compile(r"^(19|20)\d{2}$")
_POSTAL_CODE_PATTERN = re.compile(r"^\d{4}$")
_COORDINATE_PATTERN = re.compile(r"^[+-]?\d+(?:\.\d+)?$")
_COORDINATE_NAMES = {"latitude", "longitude", "lat", "lon", "lng"}
_POSTAL_NAMES = {"npa", "zip", "codepostal", "code_postal"}


def _empty_str_list() -> list[str]:
    return []


class SupportsColumnStats(Protocol):
    min: float | None
    max: float | None
    mean: float | None
    median: float | None


class SupportsColumn(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def detected_type(self) -> str: ...

    @property
    def fill_rate(self) -> float: ...

    @property
    def sample_values(self) -> Sequence[str]: ...

    @property
    def stats(self) -> SupportsColumnStats | None: ...


class SupportsExploredResource(Protocol):
    @property
    def columns(self) -> Sequence[SupportsColumn]: ...

    @property
    def row_count(self) -> int: ...


class SupportsResourceMetadata(Protocol):
    @property
    def dataset_title(self) -> str | None: ...


@dataclass(slots=True)
class Analysis:
    """Resultat d'analyse heuristique exposable via l'API."""

    summary: str
    capabilities: list[str] = field(default_factory=_empty_str_list)
    caveats: list[str] = field(default_factory=_empty_str_list)


def analyse_explored_resource(
    explored: SupportsExploredResource,
    metadata: SupportsResourceMetadata,
) -> Analysis:
    """Produit une analyse actionnable a partir de la structure detectee."""

    has_geo = any(_is_geographic(column) for column in explored.columns)
    has_temporal = any(_is_temporal(column) for column in explored.columns)
    numeric_columns = [column for column in explored.columns if _is_numeric(column)]
    categorical_columns = [column for column in explored.columns if _is_categorical(column)]
    identifier_columns = [column for column in explored.columns if _is_identifier(column)]

    title = (metadata.dataset_title or "Ce dataset").strip() or "Ce dataset"
    summary = _build_summary(title, has_geo, has_temporal, bool(numeric_columns))

    capabilities: list[str] = []
    if has_geo and numeric_columns:
        capabilities.append("Comparer des territoires et projeter les mesures sur une carte.")
    if has_temporal and numeric_columns:
        capabilities.append("Suivre l'evolution temporelle des mesures et detecter des tendances.")
    if has_geo and has_temporal and numeric_columns:
        capabilities.append("Construire un tableau de bord geographique et chronologique.")
    if numeric_columns:
        capabilities.append(
            "Calculer des statistiques descriptives et reperer les amplitudes utiles."
        )
    if categorical_columns:
        capabilities.append("Segmenter les observations par categorie pour filtrer ou comparer.")
    if identifier_columns:
        capabilities.append(
            "Croiser ce jeu avec d'autres sources via des identifiants ou codes stables."
        )
    if not capabilities:
        capabilities.append(
            "Explorer les colonnes detectees pour confirmer la structure "
            "avant une analyse plus poussee."
        )

    caveats = _build_caveats(explored.columns, explored.row_count)
    return Analysis(summary=summary, capabilities=capabilities, caveats=caveats)


def _build_summary(title: str, has_geo: bool, has_temporal: bool, has_numeric: bool) -> str:
    if has_geo and has_temporal and has_numeric:
        return f"{title} combine des dimensions geographiques, temporelles et numeriques."
    if has_geo and has_numeric:
        return f"{title} contient des mesures numeriques rattachees a des territoires."
    if has_temporal and has_numeric:
        return f"{title} permet de lire une evolution temporelle sur des mesures chiffrees."
    if has_numeric:
        return f"{title} propose des mesures chiffrees exploitables pour des comparaisons simples."
    if has_geo:
        return f"{title} semble decrire une structure geographique ou territoriale."
    if has_temporal:
        return f"{title} met en evidence une structure temporelle exploitable."
    return f"{title} expose une structure exploitable, a confirmer avec le contenu complet."


def _build_caveats(columns: Sequence[SupportsColumn], row_count: int) -> list[str]:
    caveats = ["Analyse heuristique basee sur les colonnes detectees et un echantillon limite."]

    weak_columns = [column.name for column in columns if column.fill_rate < 0.8]
    if weak_columns:
        names = ", ".join(weak_columns[:3])
        caveats.append(f"Taux de remplissage faible sur: {names}.")

    if row_count <= 5:
        caveats.append("Peu de lignes observees: confirmer les hypotheses sur le fichier complet.")

    if not any(_is_temporal(column) for column in columns):
        caveats.append("Aucune dimension temporelle nette detectee dans cet apercu.")

    return caveats


def _is_geographic(column: SupportsColumn) -> bool:
    normalized = _normalize(column.name)
    if normalized in _SWISS_LOCALITY_NAMES:
        return True
    if normalized in _COORDINATE_NAMES:
        return True
    if normalized in _POSTAL_NAMES:
        return True

    sample_values = [value.strip() for value in column.sample_values if value.strip()]
    if normalized in _COORDINATE_NAMES:
        return all(_COORDINATE_PATTERN.match(value) for value in sample_values)
    if normalized in _POSTAL_NAMES:
        return any(_POSTAL_CODE_PATTERN.match(value) for value in sample_values)
    return False


def _is_temporal(column: SupportsColumn) -> bool:
    normalized = _normalize(column.name)
    if normalized in _TEMPORAL_NAMES:
        return True
    if column.detected_type == "date":
        return True
    if normalized in {"annee", "year", "jahr"}:
        return all(
            _YEAR_PATTERN.match(value.strip()) for value in column.sample_values if value.strip()
        )
    return False


def _is_numeric(column: SupportsColumn) -> bool:
    return column.detected_type in {"integer", "float"} and column.stats is not None


def _is_categorical(column: SupportsColumn) -> bool:
    normalized = _normalize(column.name)
    distinct_samples = {value.strip().lower() for value in column.sample_values if value.strip()}
    if normalized in _CATEGORICAL_NAMES and column.fill_rate >= 0.8:
        return True
    return (
        column.detected_type == "string"
        and 1 < len(distinct_samples) <= 5
        and column.fill_rate >= 0.8
    )


def _is_identifier(column: SupportsColumn) -> bool:
    normalized = _normalize(column.name)
    return normalized in _IDENTIFIER_NAMES


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.strip().lower())

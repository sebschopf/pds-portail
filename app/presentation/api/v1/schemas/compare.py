"""Schemas pour la comparaison de datasets (PDS-43)."""

from __future__ import annotations

from pydantic import BaseModel, Field

MAX_COMPARE_IDS = 4
"""Nombre maximal de datasets comparables simultanement."""


class CompareItem(BaseModel):
    """Dataset comparable : champs homogenes pour le tableau comparatif.

    Contrat strict (ADR-035) : tous les champs sont requis, valeurs nulles explicites.
    """

    id: str
    title: str
    org_name: str | None
    description: str | None
    license: str | None
    quality_score: int | None
    completeness: int | None
    freshness_days: int | None
    resource_formats: list[str]
    resource_count: int
    tags: list[str]
    ckan_url: str | None


class CompareRequest(BaseModel):
    """Requete de comparaison : liste d'IDs de datasets (2 a 4)."""

    ids: list[str] = Field(
        ...,
        min_length=2,
        max_length=MAX_COMPARE_IDS,
        description="IDs des datasets a comparer (2 a 4)",
    )


class CompareResponse(BaseModel):
    """Reponse de comparaison : liste de datasets comparables."""

    items: list[CompareItem] = Field(description="Datasets comparables (2 a 4)")

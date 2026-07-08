"""Schemas pour la recherche dataset."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RankingSignals(BaseModel):
    """Signaux de ranking hybride PDS-40, contrat strict ADR-035."""

    hybrid_score: float
    text_score: float
    quality_normalized: float
    freshness_component: float
    weight_text: float
    weight_quality: float
    weight_freshness: float


class SearchDatasetItem(BaseModel):
    """Dataset dans les resultats de recherche (card minimale).

    Contrat strict (ADR-035) : tous les champs sont requis, valeurs nulles explicites.
    """

    id: str
    title: str
    org_name: str | None
    description: str | None
    quality_score: int | None
    completeness: int | None
    freshness_days: int | None
    resource_formats: list[str]
    resource_count: int
    tags: list[str]
    ranking_signals: RankingSignals | None


class FacetItem(BaseModel):
    """Item de facette (organisation, format, tag)."""

    name: str
    count: int
    display_name: str | None = None


class SearchFacets(BaseModel):
    """Facettes d'agrégation pour la recherche."""

    organizations: list[FacetItem] = []
    formats: list[FacetItem] = []
    tags: list[FacetItem] = []


class SearchResponse(BaseModel):
    """Reponse paginee de recherche dataset."""

    total: int = Field(description="Nombre total de resultats")
    offset: int = Field(default=0, description="Offset pagination")
    limit: int = Field(description="Limite par page")
    datasets: list[SearchDatasetItem]
    facets: SearchFacets | None = None


class TopQueryItem(BaseModel):
    """Requete la plus frequente dans le cache applicatif."""

    query_key: str = Field(description="Cle de cache (contient les parametres de requete)")
    endpoint_type: str = Field(description="Type d'endpoint (search, dataset_detail)")
    hit_count: int = Field(description="Nombre de hits cumules")
    created_at: str = Field(description="Date de derniere mise en cache")


class TopQueriesResponse(BaseModel):
    """Liste des N requetes les plus frequentes."""

    queries: list[TopQueryItem] = Field(description="Requetes triees par hit_count decroissant")


class ZeroResultItem(BaseModel):
    """Requete n'ayant retourne aucun resultat."""

    query_key: str = Field(description="Cle de cache")
    endpoint_type: str = Field(description="Type d'endpoint (search, dataset_detail)")
    created_at: str = Field(description="Date de mise en cache")
    response_total: int = Field(0, description="Valeur du champ total dans la reponse")


class ZeroResultsResponse(BaseModel):
    """Liste des requetes sans resultat (total=0)."""

    queries: list[ZeroResultItem] = Field(description="Requetes avec total=0 dans le response_json")
    count: int = Field(description="Nombre total de requetes sans resultat")

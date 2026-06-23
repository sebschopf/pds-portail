"""Schemas Pydantic pour les endpoints de recherche et détail dataset.

Normalisent et enrichissent les reponses CKAN via les indicateurs de qualite
et la structure dataset explicitee.
"""

from pydantic import BaseModel, Field


class ResourceResponse(BaseModel):
    """Ressource (fichier/endpoint) normalise."""

    id: str
    name: str
    format: str | None = None
    url: str | None = None
    size_bytes: int | None = None
    created: str | None = None
    last_modified: str | None = None


class SearchDatasetItem(BaseModel):
    """Dataset dans les resultats de recherche (card minimale)."""

    id: str
    title: str
    org_name: str | None = None
    description: str | None = None
    quality_score: int | None = Field(None, description="Score qualite 0-100")
    completeness: int | None = Field(None, description="Completude metadata 0-100")
    freshness_days: int | None = Field(None, description="Jours depuis derniere MAJ")
    resource_formats: list[str] = Field(default_factory=list)
    resource_count: int = 0
    tags: list[str] = Field(default_factory=list)
    ranking_signals: dict[str, float] | None = Field(
        None,
        description=(
            "Signaux de ranking hybride: hybrid_score, text_score, quality_normalized, "
            "freshness_component, weight_text, weight_quality, weight_freshness"
        ),
    )


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


class DatasetStructure(BaseModel):
    """Structure explicitee du dataset pour comprehension par utilisateurs non-techniques."""

    fields: list[str] = Field(default_factory=list, description="Champs/colonnes du dataset")
    formats: list[str] = Field(default_factory=list, description="Formats des ressources")
    update_frequency: str | None = Field(None, description="Frequence MAJ esperee")
    last_updated: str | None = Field(None, description="Date derniere MAJ")


class AccessMode(BaseModel):
    """Mode d'acces au dataset (direct, exploration, API)."""

    type: str = Field(description="Type: 'direct_download', 'exploration', 'api'")
    label: str = Field(description="Label lisible pour utilisateur")
    description: str | None = None
    url: str | None = None


class DatasetDetailResponse(BaseModel):
    """Detail complet du dataset avec structure et indicateurs."""

    id: str
    title: str
    description: str | None = None
    org_id: str | None = None
    org_name: str | None = None
    license: str | None = None
    author: str | None = None
    created: str | None = None
    modified: str | None = None
    quality_score: int | None = Field(None, description="Score qualite 0-100")
    completeness: int | None = Field(None, description="Completude metadata 0-100")
    freshness_days: int | None = Field(None, description="Jours depuis derniere MAJ")
    dataset_structure: DatasetStructure
    access_modes: list[AccessMode] = []
    resources: list[ResourceResponse] = []
    tags: list[str] = Field(default_factory=list)
    ckan_url: str | None = None


class ResourceDetailResponse(BaseModel):
    """Detail complet de ressource avec reference au dataset."""

    id: str
    name: str
    format: str | None = None
    url: str | None = None
    size_bytes: int | None = None
    created: str | None = None
    last_modified: str | None = None
    dataset_id: str | None = None
    dataset_title: str | None = None

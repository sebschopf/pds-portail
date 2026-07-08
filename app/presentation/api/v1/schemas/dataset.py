"""Schemas pour le detail dataset et l'exploration de ressource."""

from __future__ import annotations

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
    """Detail complet du dataset avec structure et indicateurs.

    Contrat partiel (ADR-035) : dataset_structure, resources, tags obligatoires.
    Les champs nullables conservent = None pour compatibilité tests internes.
    """

    id: str
    title: str
    description: str | None
    org_id: str | None
    org_name: str | None
    license: str | None
    author: str | None
    created: str | None
    modified: str | None
    quality_score: int | None
    completeness: int | None
    freshness_days: int | None
    dataset_structure: DatasetStructure
    access_modes: list[AccessMode]
    resources: list[ResourceResponse]
    tags: list[str]
    ckan_url: str | None


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


class ColumnStats(BaseModel):
    """Statistiques descriptives pour une colonne numerique."""

    min: float | None = Field(None, description="Valeur minimale")
    max: float | None = Field(None, description="Valeur maximale")
    mean: float | None = Field(None, description="Moyenne arithmetique")
    median: float | None = Field(None, description="Mediane")


class ColumnInfo(BaseModel):
    """Information sur une colonne detectee dans le fichier explore."""

    name: str = Field(description="Nom de la colonne")
    detected_type: str = Field(
        description="Type detecte: 'string', 'integer', 'float', 'date', 'unknown'"
    )
    fill_rate: float = Field(description="Taux de remplissage (0.0-1.0)", ge=0.0, le=1.0)
    sample_values: list[str] = Field(
        default_factory=list, description="Echantillon de valeurs (max 5)"
    )
    stats: ColumnStats | None = Field(None, description="Statistiques numeriques (si applicable)")


class ResourceAnalysis(BaseModel):
    """Analyse heuristique actionnable de la ressource exploree."""

    summary: str = Field(description="Resume interpretable de la structure detectee")
    capabilities: list[str] = Field(
        default_factory=list,
        description="Usages ou visualisations suggeres a partir des signaux detectes",
    )
    caveats: list[str] = Field(
        default_factory=list,
        description="Limites et points d'attention observes sur l'aperçu",
    )


def _empty_column_info_list() -> list[ColumnInfo]:
    return []


class ExploreResourceResponse(BaseModel):
    """Reponse du parsing et de l'analyse d'une ressource (CSV/JSON)."""

    resource_id: str = Field(description="ID de la ressource")
    format: str = Field(description="Format du fichier (csv, json)")
    parsed_at: str = Field(description="Horodatage du parsing (ISO 8601)")
    columns: list[ColumnInfo] = Field(
        default_factory=_empty_column_info_list,
        description="Colonnes detectees",
    )
    row_count: int = Field(default=0, description="Nombre de lignes/enregistrements")
    analysis: ResourceAnalysis | None = Field(
        default=None,
        description="Analyse heuristique contextualisee a partir des colonnes detectees",
    )
    cached: bool = Field(
        default=False,
        description="True si le resultat provient du cache (moins de 24h)",
    )

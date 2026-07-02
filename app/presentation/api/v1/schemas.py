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


# --- Schemas pour la comparaison guidee (PDS-43) ---

MAX_COMPARE_IDS = 4
"""Nombre maximal de datasets comparables simultanement."""


class CompareRequest(BaseModel):
    """Requete de comparaison : liste d'IDs de datasets (2 a 4)."""

    ids: list[str] = Field(
        ...,
        min_length=2,
        max_length=MAX_COMPARE_IDS,
        description="IDs des datasets a comparer (2 a 4)",
    )


class CompareItem(BaseModel):
    """Dataset comparable : champs homogenes pour le tableau comparatif."""

    id: str
    title: str
    org_name: str | None = None
    description: str | None = None
    license: str | None = None
    quality_score: int | None = Field(None, description="Score qualite 0-100")
    completeness: int | None = Field(None, description="Completude metadata 0-100")
    freshness_days: int | None = Field(None, description="Jours depuis derniere MAJ")
    resource_formats: list[str] = Field(default_factory=list)
    resource_count: int = 0
    tags: list[str] = Field(default_factory=list)
    ckan_url: str | None = None


class CompareResponse(BaseModel):
    """Reponse de comparaison : liste de datasets comparables."""

    items: list[CompareItem] = Field(description="Datasets comparables (2 a 4)")


# --- Schemas pour les metriques d'usage (PDS-58) ---


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


# --- Schemas pour l'exploration de ressource (PDS-81/82) ---


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


class ExploreResourceResponse(BaseModel):
    """Reponse du parsing d'une ressource (CSV/JSON)."""

    resource_id: str = Field(description="ID de la ressource")
    format: str = Field(description="Format du fichier (csv, json)")
    parsed_at: str = Field(description="Horodatage du parsing (ISO 8601)")
    columns: list[ColumnInfo] = Field(default_factory=list, description="Colonnes detectees")
    row_count: int = Field(default=0, description="Nombre de lignes/enregistrements")
    cached: bool = Field(
        default=False,
        description="True si le resultat provient du cache (moins de 24h)",
    )

"""Schemas Pydantic pour les endpoints de recherche et détail dataset.

Normalisent et enrichissent les reponses CKAN via les indicateurs de qualite
et la structure dataset explicitee.
"""

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


# --- Schemas router v1 (watchers/internal/sync) ---


class HealthResponse(BaseModel):
    """Reponse minimale de sante service/cache."""

    status: str
    last_sync: str | None


class CacheCountsResponse(BaseModel):
    """Compteurs minimaux du cache."""

    organizations: int
    datasets: int
    resources: int


class InternalCacheResponse(BaseModel):
    """Vue interne pour verifier qu'un cache peuple est consultable."""

    status: str
    last_sync: str | None
    cache_populated: bool
    counts: CacheCountsResponse


class WatcherCreateRequest(BaseModel):
    """Requete de creation d'une surveillance dataset."""

    email: str
    dataset_id: str


class WatcherCreateResponse(BaseModel):
    """Reponse de creation de watcher/surveillance."""

    watcher_id: str
    email: str
    token: str
    dataset_id: str
    status: str


class WatchedDatasetItemResponse(BaseModel):
    """Element de dataset surveille expose a l'utilisateur."""

    id: str
    dataset_id: str
    dataset_title: str | None
    created_at: str


class WatchersListResponse(BaseModel):
    """Liste des datasets surveilles pour un token watcher."""

    watcher_id: str
    email: str
    status: str
    items: list[WatchedDatasetItemResponse]


class AlertItemResponse(BaseModel):
    """Entree d'alerte pour un changement detecte."""

    id: str
    dataset_id: str
    dataset_title: str | None
    change_type: str
    previous_value: str | None
    new_value: str | None
    detected_at: str
    notified_at: str | None


class AlertsResponse(BaseModel):
    """Reponse de consultation des alertes d'un watcher."""

    watcher_id: str
    count: int
    items: list[AlertItemResponse]


class MagicLinkConsumeResponse(BaseModel):
    """Réponse après consommation réussie d'un magic link (ADR-030)."""

    token: str
    watcher_id: str
    email: str
    status: str


class MagicLinkRequestBody(BaseModel):
    """Corps de la requête pour demander un nouveau magic link par email."""

    email: str


class InternalSupportWatcherLookupResponse(BaseModel):
    """Vue redigée pour retrouver un watcher par email côté support."""

    watcher_id: str
    watcher_status: str
    subscription_id_present: bool
    watched_datasets_count: int
    last_webhook_at: str | None
    last_magic_link_at: str | None


class InternalSupportSubscriptionResponse(BaseModel):
    """Etat redigé d'un abonnement watcher pour le support interne."""

    watcher_id: str
    subscription_state: str
    subscription_id_masked: str | None
    updated_at: str


class InternalSupportWebhookEventResponse(BaseModel):
    """Evenement webhook redigé expose par le support interne."""

    event_type: str
    received_at: str
    delivery_status: str
    correlation_id: str | None


class InternalSupportWebhookEventsResponse(BaseModel):
    """Historique recent des webhooks Polar associes a un watcher."""

    watcher_id: str
    items: list[InternalSupportWebhookEventResponse]


class InternalSupportMagicLinkStateResponse(BaseModel):
    """Etat des magic links temporaires pour le support interne."""

    watcher_id: str
    last_issued_at: str | None
    last_used_at: str | None
    active_unexpired_count: int
    expired_unconsumed_count: int


class InternalSupportEmailDeliverabilityResponse(BaseModel):
    """Indicateurs rediges sur l'envoi email pour un watcher."""

    watcher_id: str
    last_send_status: str | None
    last_send_at: str | None
    provider_message_id_masked: str | None
    recent_error_code: str | None
    recent_error_count_24h: int


class InternalSupportMagicLinkResendRequest(BaseModel):
    """Corps de la requête de renvoi de magic link support."""

    reason: str


class InternalSupportMagicLinkResendResponse(BaseModel):
    """Réponse auditee d'un renvoi de magic link support."""

    audit_id: str
    dispatch_status: str
    issued_at: str


class SyncStatusResponse(BaseModel):
    """Etat de la synchronisation CKAN incrementale."""

    ckan_offset: int
    updated_at: str | None


class SyncMetricsItem(BaseModel):
    """Metriques d'un cycle de sync unique (PDS-45)."""

    id: int
    synced_datasets: int
    synced_organizations: int
    synced_resources: int
    errors: int
    mode: str
    duration_ms: int
    started_at: str
    completed_at: str


class SyncMetricsResponse(BaseModel):
    """Historique des metriques d'ingestion (PDS-45)."""

    items: list[SyncMetricsItem]
    total: int


class CacheStatsResponse(BaseModel):
    """Statistiques de hit/miss du cache applicatif (PDS-46)."""

    hits: int
    misses: int
    stale_entries: int
    total_entries: int
    hit_ratio: float


class ContactRequest(BaseModel):
    """Formulaire de contact public (PDS-122.1)."""

    email: str = Field(
        description="Email de l'utilisateur pour la réponse",
        min_length=5,
        max_length=254,
    )
    concerne: str = Field(
        description="Catégorie du message",
        pattern=r"^(surveillance|paiement|donnees|technique|autre)$",
    )
    message: str = Field(
        description="Message de l'utilisateur",
        min_length=10,
        max_length=5000,
    )

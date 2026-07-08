"""Schemas internes : sante, cache, sync, support, contact."""

from __future__ import annotations

from pydantic import BaseModel, Field


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
        description="Email de l'utilisateur pour la reponse",
        min_length=5,
        max_length=254,
    )
    concerne: str = Field(
        description="Categorie du message",
        pattern=r"^(surveillance|paiement|donnees|technique|autre)$",
    )
    message: str = Field(
        description="Message de l'utilisateur",
        min_length=10,
        max_length=5000,
    )


class InternalSupportWatcherLookupResponse(BaseModel):
    """Vue redigee pour retrouver un watcher par email cote support."""

    watcher_id: str
    watcher_status: str
    subscription_id_present: bool
    watched_datasets_count: int
    last_webhook_at: str | None
    last_magic_link_at: str | None


class InternalSupportSubscriptionResponse(BaseModel):
    """Etat redige d'un abonnement watcher pour le support interne."""

    watcher_id: str
    subscription_state: str
    subscription_id_masked: str | None
    updated_at: str


class InternalSupportWebhookEventResponse(BaseModel):
    """Evenement webhook redige expose par le support interne."""

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
    """Corps de la requete de renvoi de magic link support."""

    reason: str


class InternalSupportMagicLinkResendResponse(BaseModel):
    """Reponse auditee d'un renvoi de magic link support."""

    audit_id: str
    dispatch_status: str
    issued_at: str

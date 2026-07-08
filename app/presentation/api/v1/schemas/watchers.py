"""Schemas pour les watchers, alertes et magic links."""

from __future__ import annotations

from pydantic import BaseModel


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

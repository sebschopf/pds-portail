"""Ports (interfaces) pour la persistance des watchers et datasets surveillés.

Référence : SPEC-009 §3.1, ADR-028 (PDS-85), PDS-86.
"""

from typing import NamedTuple, Protocol


class Watcher(NamedTuple):
    """Représentation métier d'un abonné à la surveillance."""

    id: str
    email: str
    polar_subscription_id: str | None
    plan: str  # 'monthly' | 'yearly'
    status: str  # 'active' | 'cancelled' | 'paused'
    token: str  # UUID v4, clé d'accès à /alertes
    created_at: str  # ISO 8601
    updated_at: str  # ISO 8601


class WatchedDataset(NamedTuple):
    """Représentation métier d'un dataset surveillé par un watcher."""

    id: str
    watcher_id: str
    dataset_id: str
    last_known_metadata_modified: str | None
    last_known_resource_count: int | None
    last_known_quality_score: float | None
    created_at: str  # ISO 8601


class WatcherRepositoryPort(Protocol):
    """Port pour gérer les watchers et leurs datasets surveillés."""

    def create(
        self,
        email: str,
        token: str,
        plan: str = "monthly",
        polar_subscription_id: str | None = None,
    ) -> Watcher:
        """Crée un nouveau watcher actif.

        Retourne le watcher créé.
        """
        ...

    def find_by_email(self, email: str) -> Watcher | None:
        """Cherche un watcher par email.

        Retourne None si inexistant.
        """
        ...

    def find_by_token(self, token: str) -> Watcher | None:
        """Cherche un watcher par son token d'accès.

        Retourne None si inexistant.
        """
        ...

    def find_by_dataset(self, dataset_id: str) -> list[Watcher]:
        """Retourne tous les watchers actifs surveillant un dataset donné."""
        ...

    def list_active(self) -> list[Watcher]:
        """Retourne tous les watchers avec status='active'."""
        ...

    def list_watched_datasets(self) -> list[WatchedDataset]:
        """Retourne tous les datasets actuellement surveillés."""
        ...

    def update_status(self, watcher_id: str, status: str) -> None:
        """Met à jour le status d'un watcher (active/cancelled/paused)."""
        ...

    def add_watched_dataset(
        self,
        watcher_id: str,
        dataset_id: str,
        last_known_metadata_modified: str | None = None,
        last_known_resource_count: int | None = None,
        last_known_quality_score: float | None = None,
    ) -> WatchedDataset:
        """Ajoute un dataset à surveiller pour un watcher.

        Lève une exception si le couple (watcher_id, dataset_id) existe déjà.
        """
        ...

    def remove_watched_dataset(self, watcher_id: str, dataset_id: str) -> None:
        """Supprime la surveillance d'un dataset pour un watcher."""
        ...

    def update_last_known(
        self,
        watcher_id: str,
        dataset_id: str,
        metadata_modified: str | None,
        resource_count: int | None,
        quality_score: float | None,
    ) -> None:
        """Met à jour les dernières valeurs connues d'un dataset surveillé."""
        ...

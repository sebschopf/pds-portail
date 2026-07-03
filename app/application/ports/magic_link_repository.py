"""Port pour la persistance des magic links temporaires."""

from typing import NamedTuple, Protocol


class MagicLink(NamedTuple):
    """Représentation métier d'un magic link temporaire."""

    id: str
    watcher_id: str
    token_hash: str
    created_at: str
    expires_at: str
    used_at: str | None


class MagicLinkRepositoryPort(Protocol):
    """Port pour créer et mettre à jour les magic links."""

    def create(
        self,
        watcher_id: str,
        token_hash: str,
        created_at: str,
        expires_at: str,
    ) -> MagicLink:
        """Crée un magic link temporaire."""

    def find_by_token_hash(self, token_hash: str) -> MagicLink | None:
        """Cherche un magic link par hash SHA-256 du token brut."""

    def mark_used(self, magic_link_id: str, used_at: str) -> None:
        """Marque un magic link comme consommé."""

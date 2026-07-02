from typing import NamedTuple, Protocol


class License(NamedTuple):
    """Représentation métier d'une licence API."""

    id: str
    key_hash: str
    plan: str  # 'basic' | 'pro'
    quota_monthly: int
    used_this_month: int
    created_at: str  # ISO 8601
    expires_at: str | None  # ISO 8601 nullable


class LicenseRepositoryPort(Protocol):
    """Port pour gérer les licences API (clés d'accès)."""

    def find_by_key_hash(self, key_hash: str) -> License | None:
        """Cherche une licence par le hash SHA-256 de sa clé.

        Retourne None si la clé n'existe pas, la licence sinon.
        """

    def increment_usage(self, license_id: str) -> None:
        """Incrémente `used_this_month` pour une licence.

        Lève une exception si la licence n'existe pas ou si le quota est dépassé
        (check avec CONSTRAINT au niveau SQL).
        """

    def create(
        self,
        key_hash: str,
        plan: str,
        quota_monthly: int,
        expires_at: str | None = None,
    ) -> License:
        """Crée une nouvelle licence (côté admin/backoffice).

        Retourne la licence créée.
        """

    def reset_monthly_usage(self) -> None:
        """Réinitialise `used_this_month` à 0 pour toutes les licences.

        À appeler le 1er du mois (tâche batch).
        """

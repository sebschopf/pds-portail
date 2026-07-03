"""Port (interface) pour la persistance du journal des changements détectés.

Référence : SPEC-009 §3.1, PDS-86.
"""

from typing import NamedTuple, Protocol


class ChangeLogEntry(NamedTuple):
    """Représentation métier d'une entrée dans le journal des changements."""

    id: str
    dataset_id: str
    change_type: str  # ex : 'metadata_modified' | 'resource_count' | 'quality_score'
    previous_value: str | None
    new_value: str | None
    detected_at: str  # ISO 8601
    notified_at: str | None  # ISO 8601, None tant que non envoyé


class ChangeLogRepositoryPort(Protocol):
    """Port pour écrire et lire le journal des changements détectés."""

    def insert(
        self,
        dataset_id: str,
        change_type: str,
        previous_value: str | None,
        new_value: str | None,
        detected_at: str,
    ) -> ChangeLogEntry:
        """Insère une nouvelle entrée de changement.

        Retourne l'entrée créée avec notified_at=None.
        """

    def find_unnotified(self) -> list[ChangeLogEntry]:
        """Retourne toutes les entrées dont notified_at est NULL.

        Utilisé par le use-case d'envoi d'alertes (PDS-88).
        """

    def find_last_notified_at(self, dataset_id: str) -> str | None:
        """Retourne le dernier horodatage notified_at pour un dataset donné.

        Utilisé pour appliquer le rate limiting 24h par dataset avant envoi.
        """

    def mark_notified(self, entry_id: str, notified_at: str) -> None:
        """Marque une entrée comme notifiée en renseignant notified_at."""

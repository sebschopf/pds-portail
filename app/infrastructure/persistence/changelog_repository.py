"""Repository SQLAlchemy pour le journal des changements détectés.

Implémentation concrète du port ChangeLogRepositoryPort (SPEC-009, PDS-86).
"""

import logging
import uuid

from sqlalchemy import select

from app.application.ports.changelog_repository import ChangeLogEntry
from app.infrastructure.persistence.database import SessionLocal
from app.infrastructure.persistence.models import ChangeLogModel

logger = logging.getLogger(__name__)


def _model_to_entry(model: ChangeLogModel) -> ChangeLogEntry:
    return ChangeLogEntry(
        id=model.id,
        dataset_id=model.dataset_id,
        change_type=model.change_type,
        previous_value=model.previous_value,
        new_value=model.new_value,
        detected_at=model.detected_at,
        notified_at=model.notified_at,
    )


class SqlAlchemyChangeLogRepository:
    """Repository pour le journal des changements détectés sur les datasets."""

    def insert(
        self,
        dataset_id: str,
        change_type: str,
        previous_value: str | None,
        new_value: str | None,
        detected_at: str,
    ) -> ChangeLogEntry:
        """Insère une nouvelle entrée de changement."""
        model = ChangeLogModel(
            id=str(uuid.uuid4()),
            dataset_id=dataset_id,
            change_type=change_type,
            previous_value=previous_value,
            new_value=new_value,
            detected_at=detected_at,
            notified_at=None,
        )
        with SessionLocal() as session:
            session.add(model)
            session.commit()
            session.refresh(model)
            return _model_to_entry(model)

    def find_unnotified(self) -> list[ChangeLogEntry]:
        """Retourne toutes les entrées dont notified_at est NULL."""
        with SessionLocal() as session:
            stmt = select(ChangeLogModel).where(ChangeLogModel.notified_at.is_(None))
            models = session.execute(stmt).scalars().all()
            return [_model_to_entry(m) for m in models]

    def find_last_notified_at(self, dataset_id: str) -> str | None:
        """Retourne le dernier notified_at connu pour un dataset."""
        with SessionLocal() as session:
            stmt = (
                select(ChangeLogModel.notified_at)
                .where(
                    ChangeLogModel.dataset_id == dataset_id,
                    ChangeLogModel.notified_at.is_not(None),
                )
                .order_by(ChangeLogModel.notified_at.desc())
                .limit(1)
            )
            value = session.execute(stmt).scalar_one_or_none()
            return value

    def mark_notified(self, entry_id: str, notified_at: str) -> None:
        """Marque une entrée comme notifiée."""
        with SessionLocal() as session:
            stmt = select(ChangeLogModel).where(ChangeLogModel.id == entry_id)
            model = session.execute(stmt).scalar_one_or_none()
            if not model:
                raise ValueError(f"ChangeLogEntry {entry_id} introuvable.")
            model.notified_at = notified_at
            session.commit()

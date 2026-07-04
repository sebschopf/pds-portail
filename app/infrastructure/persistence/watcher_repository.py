"""Repository SQLAlchemy pour la gestion des watchers et datasets surveillés.

Implémentation concrète du port WatcherRepositoryPort (SPEC-009, PDS-86).
"""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.application.ports.watcher_repository import WatchedDataset, Watcher
from app.infrastructure.persistence.database import SessionLocal
from app.infrastructure.persistence.models import WatchedDatasetModel, WatcherModel

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _model_to_watcher(model: WatcherModel) -> Watcher:
    return Watcher(
        id=model.id,
        email=model.email,
        polar_subscription_id=model.polar_subscription_id,
        plan=model.plan,
        status=model.status,
        token=model.token,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _model_to_watched_dataset(model: WatchedDatasetModel) -> WatchedDataset:
    return WatchedDataset(
        id=model.id,
        watcher_id=model.watcher_id,
        dataset_id=model.dataset_id,
        last_known_metadata_modified=model.last_known_metadata_modified,
        last_known_resource_count=model.last_known_resource_count,
        last_known_quality_score=model.last_known_quality_score,
        created_at=model.created_at,
    )


class SqlAlchemyWatcherRepository:
    """Repository pour les watchers (abonnés surveillance de datasets)."""

    def create(
        self,
        email: str,
        token: str,
        plan: str = "monthly",
        polar_subscription_id: str | None = None,
    ) -> Watcher:
        """Crée un nouveau watcher actif."""
        now = _now_iso()
        model = WatcherModel(
            id=str(uuid.uuid4()),
            email=email,
            polar_subscription_id=polar_subscription_id,
            plan=plan,
            status="active",
            token=token,
            created_at=now,
            updated_at=now,
        )
        with SessionLocal() as session:
            session.add(model)
            session.commit()
            session.refresh(model)
            return _model_to_watcher(model)

    def find_by_email(self, email: str) -> Watcher | None:
        """Cherche un watcher par email."""
        with SessionLocal() as session:
            stmt = select(WatcherModel).where(WatcherModel.email == email)
            model = session.execute(stmt).scalar_one_or_none()
            return _model_to_watcher(model) if model else None

    def find_by_token(self, token: str) -> Watcher | None:
        """Cherche un watcher par son token d'accès."""
        with SessionLocal() as session:
            stmt = select(WatcherModel).where(WatcherModel.token == token)
            model = session.execute(stmt).scalar_one_or_none()
            return _model_to_watcher(model) if model else None

    def find_by_polar_subscription_id(self, polar_subscription_id: str) -> Watcher | None:
        """Cherche un watcher par son identifiant d'abonnement Polar."""
        with SessionLocal() as session:
            stmt = select(WatcherModel).where(
                WatcherModel.polar_subscription_id == polar_subscription_id
            )
            model = session.execute(stmt).scalar_one_or_none()
            return _model_to_watcher(model) if model else None

    def find_by_dataset(self, dataset_id: str) -> list[Watcher]:
        """Retourne tous les watchers actifs surveillant un dataset donné."""
        with SessionLocal() as session:
            stmt = (
                select(WatcherModel)
                .join(WatchedDatasetModel, WatchedDatasetModel.watcher_id == WatcherModel.id)
                .where(
                    WatchedDatasetModel.dataset_id == dataset_id,
                    WatcherModel.status == "active",
                )
            )
            models = session.execute(stmt).scalars().all()
            return [_model_to_watcher(m) for m in models]

    def list_active(self) -> list[Watcher]:
        """Retourne tous les watchers actifs."""
        with SessionLocal() as session:
            stmt = select(WatcherModel).where(WatcherModel.status == "active")
            models = session.execute(stmt).scalars().all()
            return [_model_to_watcher(m) for m in models]

    def list_watched_datasets(self) -> list[WatchedDataset]:
        """Retourne tous les datasets actuellement surveillés."""
        with SessionLocal() as session:
            stmt = select(WatchedDatasetModel).order_by(
                WatchedDatasetModel.dataset_id,
                WatchedDatasetModel.watcher_id,
            )
            models = session.execute(stmt).scalars().all()
            return [_model_to_watched_dataset(model) for model in models]

    def update_status(self, watcher_id: str, status: str) -> None:
        """Met à jour le status d'un watcher."""
        with SessionLocal() as session:
            stmt = select(WatcherModel).where(WatcherModel.id == watcher_id)
            model = session.execute(stmt).scalar_one_or_none()
            if not model:
                raise ValueError(f"Watcher {watcher_id} introuvable.")
            model.status = status
            model.updated_at = _now_iso()
            session.commit()

    def add_watched_dataset(
        self,
        watcher_id: str,
        dataset_id: str,
        last_known_metadata_modified: str | None = None,
        last_known_resource_count: int | None = None,
        last_known_quality_score: float | None = None,
    ) -> WatchedDataset:
        """Ajoute un dataset à surveiller.

        Lève IntegrityError si le couple (watcher_id, dataset_id) existe déjà.
        """
        model = WatchedDatasetModel(
            id=str(uuid.uuid4()),
            watcher_id=watcher_id,
            dataset_id=dataset_id,
            last_known_metadata_modified=last_known_metadata_modified,
            last_known_resource_count=last_known_resource_count,
            last_known_quality_score=last_known_quality_score,
            created_at=_now_iso(),
        )
        try:
            with SessionLocal() as session:
                session.add(model)
                session.commit()
                session.refresh(model)
                return _model_to_watched_dataset(model)
        except IntegrityError as exc:
            raise ValueError(
                f"Le dataset {dataset_id} est déjà surveillé par le watcher {watcher_id}."
            ) from exc

    def remove_watched_dataset(self, watcher_id: str, dataset_id: str) -> None:
        """Supprime la surveillance d'un dataset pour un watcher."""
        with SessionLocal() as session:
            stmt = select(WatchedDatasetModel).where(
                WatchedDatasetModel.watcher_id == watcher_id,
                WatchedDatasetModel.dataset_id == dataset_id,
            )
            model = session.execute(stmt).scalar_one_or_none()
            if model:
                session.delete(model)
                session.commit()

    def update_last_known(
        self,
        watcher_id: str,
        dataset_id: str,
        metadata_modified: str | None,
        resource_count: int | None,
        quality_score: float | None,
    ) -> None:
        """Met à jour les dernières valeurs connues d'un dataset surveillé."""
        with SessionLocal() as session:
            stmt = select(WatchedDatasetModel).where(
                WatchedDatasetModel.watcher_id == watcher_id,
                WatchedDatasetModel.dataset_id == dataset_id,
            )
            model = session.execute(stmt).scalar_one_or_none()
            if not model:
                raise ValueError(
                    f"Association watcher={watcher_id} / dataset={dataset_id} introuvable."
                )
            model.last_known_metadata_modified = metadata_modified
            model.last_known_resource_count = resource_count
            model.last_known_quality_score = quality_score
            session.commit()

    def find_last_alert_sent_at(self, watcher_id: str, dataset_id: str) -> str | None:
        """Retourne la date du dernier email d'alerte envoyé pour ce watcher+dataset."""
        with SessionLocal() as session:
            stmt = select(WatchedDatasetModel).where(
                WatchedDatasetModel.watcher_id == watcher_id,
                WatchedDatasetModel.dataset_id == dataset_id,
            )
            model = session.execute(stmt).scalar_one_or_none()
            return model.last_alert_sent_at if model else None

    def mark_alert_sent(self, watcher_id: str, dataset_id: str, sent_at: str) -> None:
        """Enregistre l'horodatage d'alerte envoyé pour ce watcher+dataset."""
        with SessionLocal() as session:
            stmt = select(WatchedDatasetModel).where(
                WatchedDatasetModel.watcher_id == watcher_id,
                WatchedDatasetModel.dataset_id == dataset_id,
            )
            model = session.execute(stmt).scalar_one_or_none()
            if not model:
                raise ValueError(
                    f"Association watcher={watcher_id} / dataset={dataset_id} introuvable."
                )
            model.last_alert_sent_at = sent_at
            session.commit()

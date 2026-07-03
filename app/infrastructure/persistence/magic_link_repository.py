"""Repository SQLAlchemy pour les magic links temporaires."""

import uuid

from sqlalchemy import select

from app.application.ports.magic_link_repository import MagicLink
from app.infrastructure.persistence.database import SessionLocal
from app.infrastructure.persistence.models import MagicLinkModel


def _model_to_magic_link(model: MagicLinkModel) -> MagicLink:
    return MagicLink(
        id=model.id,
        watcher_id=model.watcher_id,
        token_hash=model.token_hash,
        created_at=model.created_at,
        expires_at=model.expires_at,
        used_at=model.used_at,
    )


class SqlAlchemyMagicLinkRepository:
    """Repository pour la persistance des magic links temporaires."""

    def create(
        self,
        watcher_id: str,
        token_hash: str,
        created_at: str,
        expires_at: str,
    ) -> MagicLink:
        model = MagicLinkModel(
            id=str(uuid.uuid4()),
            watcher_id=watcher_id,
            token_hash=token_hash,
            created_at=created_at,
            expires_at=expires_at,
            used_at=None,
        )
        with SessionLocal() as session:
            session.add(model)
            session.commit()
            session.refresh(model)
            return _model_to_magic_link(model)

    def find_by_token_hash(self, token_hash: str) -> MagicLink | None:
        with SessionLocal() as session:
            stmt = select(MagicLinkModel).where(MagicLinkModel.token_hash == token_hash)
            model = session.execute(stmt).scalar_one_or_none()
            return _model_to_magic_link(model) if model else None

    def mark_used(self, magic_link_id: str, used_at: str) -> None:
        with SessionLocal() as session:
            stmt = select(MagicLinkModel).where(MagicLinkModel.id == magic_link_id)
            model = session.execute(stmt).scalar_one_or_none()
            if not model:
                raise ValueError(f"MagicLink {magic_link_id} introuvable.")
            model.used_at = used_at
            session.commit()

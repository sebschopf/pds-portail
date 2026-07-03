"""Tests CRUD pour le repository des magic links."""

from __future__ import annotations

import uuid
from collections.abc import Generator
from datetime import UTC, datetime

import pytest

from app.application.ports.magic_link_repository import MagicLink
from app.application.ports.watcher_repository import Watcher
from app.infrastructure.persistence.database import SessionLocal
from app.infrastructure.persistence.magic_link_repository import SqlAlchemyMagicLinkRepository
from app.infrastructure.persistence.models import MagicLinkModel, WatcherModel
from app.infrastructure.persistence.watcher_repository import SqlAlchemyWatcherRepository


def _new_token() -> str:
    return str(uuid.uuid4())


def _iso_now() -> str:
    return datetime.now(UTC).isoformat()


@pytest.fixture
def watcher_repo() -> SqlAlchemyWatcherRepository:
    return SqlAlchemyWatcherRepository()


@pytest.fixture
def magic_link_repo() -> SqlAlchemyMagicLinkRepository:
    return SqlAlchemyMagicLinkRepository()


@pytest.fixture
def created_watcher(watcher_repo: SqlAlchemyWatcherRepository) -> Generator[Watcher, None, None]:
    """Crée un watcher de test pour rattacher des magic links."""

    token = _new_token()
    watcher = watcher_repo.create(email=f"magic-{token}@example.com", token=token)
    yield watcher
    with SessionLocal() as session:
        session.query(WatcherModel).filter(WatcherModel.id == watcher.id).delete()
        session.commit()


def test_create_returns_magic_link(
    magic_link_repo: SqlAlchemyMagicLinkRepository, created_watcher: Watcher
) -> None:
    """create persiste un magic link temporaire et le retourne."""

    created_at = _iso_now()
    expires_at = _iso_now()
    magic_link = magic_link_repo.create(
        watcher_id=created_watcher.id,
        token_hash="a" * 64,
        created_at=created_at,
        expires_at=expires_at,
    )

    try:
        assert isinstance(magic_link, MagicLink)
        assert magic_link.watcher_id == created_watcher.id
        assert magic_link.used_at is None
        assert magic_link.token_hash == "a" * 64
    finally:
        with SessionLocal() as session:
            session.query(MagicLinkModel).filter(MagicLinkModel.id == magic_link.id).delete()
            session.commit()


def test_find_by_token_hash_returns_magic_link(
    magic_link_repo: SqlAlchemyMagicLinkRepository, created_watcher: Watcher
) -> None:
    """find_by_token_hash retrouve un magic link existant."""

    magic_link = magic_link_repo.create(
        watcher_id=created_watcher.id,
        token_hash="b" * 64,
        created_at=_iso_now(),
        expires_at=_iso_now(),
    )

    try:
        found = magic_link_repo.find_by_token_hash("b" * 64)
        assert found is not None
        assert found.id == magic_link.id
    finally:
        with SessionLocal() as session:
            session.query(MagicLinkModel).filter(MagicLinkModel.id == magic_link.id).delete()
            session.commit()


def test_mark_used_updates_used_at(
    magic_link_repo: SqlAlchemyMagicLinkRepository, created_watcher: Watcher
) -> None:
    """mark_used renseigne used_at sur un magic link."""

    magic_link = magic_link_repo.create(
        watcher_id=created_watcher.id,
        token_hash="c" * 64,
        created_at=_iso_now(),
        expires_at=_iso_now(),
    )

    try:
        used_at = _iso_now()
        magic_link_repo.mark_used(magic_link.id, used_at)

        with SessionLocal() as session:
            model = session.query(MagicLinkModel).filter(MagicLinkModel.id == magic_link.id).one()
            assert model.used_at == used_at
    finally:
        with SessionLocal() as session:
            session.query(MagicLinkModel).filter(MagicLinkModel.id == magic_link.id).delete()
            session.commit()

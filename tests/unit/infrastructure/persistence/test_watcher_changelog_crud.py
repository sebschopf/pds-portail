"""Tests CRUD pour WatcherRepository et ChangeLogRepository (PDS-86).

Couvre : création watcher, ajout watched_dataset, contrainte UNIQUE,
         insertion change_log, find_unnotified, mark_notified.
"""

import uuid
from collections.abc import Generator
from datetime import UTC, datetime

import pytest

from app.application.ports.changelog_repository import ChangeLogEntry
from app.application.ports.watcher_repository import WatchedDataset, Watcher
from app.infrastructure.persistence.changelog_repository import SqlAlchemyChangeLogRepository
from app.infrastructure.persistence.database import SessionLocal
from app.infrastructure.persistence.models import ChangeLogModel, WatchedDatasetModel, WatcherModel
from app.infrastructure.persistence.watcher_repository import SqlAlchemyWatcherRepository


def _new_token() -> str:
    return str(uuid.uuid4())


def _iso_now() -> str:
    return datetime.now(UTC).isoformat()


@pytest.fixture
def watcher_repo() -> SqlAlchemyWatcherRepository:
    return SqlAlchemyWatcherRepository()


@pytest.fixture
def changelog_repo() -> SqlAlchemyChangeLogRepository:
    return SqlAlchemyChangeLogRepository()


@pytest.fixture
def created_watcher(watcher_repo: SqlAlchemyWatcherRepository) -> Generator[Watcher, None, None]:
    """Crée un watcher de test et nettoie après le test."""
    token = _new_token()
    watcher = watcher_repo.create(email=f"test-{token}@example.com", token=token)
    yield watcher
    # Cleanup
    with SessionLocal() as session:
        session.query(WatcherModel).filter(WatcherModel.id == watcher.id).delete()
        session.commit()


class TestWatcherRepositoryCreate:
    """Tests de création de watcher."""

    def test_create_returns_watcher(self, watcher_repo: SqlAlchemyWatcherRepository) -> None:
        """Un watcher créé a les bons champs par défaut."""
        token = _new_token()
        email = f"create-{token}@example.com"
        watcher = watcher_repo.create(email=email, token=token)

        try:
            assert isinstance(watcher, Watcher)
            assert watcher.email == email
            assert watcher.token == token
            assert watcher.plan == "monthly"
            assert watcher.status == "active"
            assert watcher.id
        finally:
            with SessionLocal() as session:
                session.query(WatcherModel).filter(WatcherModel.id == watcher.id).delete()
                session.commit()

    def test_create_with_polar_id(self, watcher_repo: SqlAlchemyWatcherRepository) -> None:
        """Un watcher peut être créé avec un polar_subscription_id."""
        token = _new_token()
        email = f"polar-{token}@example.com"
        watcher = watcher_repo.create(
            email=email, token=token, polar_subscription_id="polar_sub_123"
        )

        try:
            assert watcher.polar_subscription_id == "polar_sub_123"
        finally:
            with SessionLocal() as session:
                session.query(WatcherModel).filter(WatcherModel.id == watcher.id).delete()
                session.commit()


class TestWatcherRepositoryFind:
    """Tests de recherche de watcher."""

    def test_find_by_email_returns_watcher(
        self,
        watcher_repo: SqlAlchemyWatcherRepository,
        created_watcher: Watcher,
    ) -> None:
        """find_by_email retrouve un watcher existant."""
        found = watcher_repo.find_by_email(created_watcher.email)
        assert found is not None
        assert found.id == created_watcher.id

    def test_find_by_email_returns_none_if_absent(
        self, watcher_repo: SqlAlchemyWatcherRepository
    ) -> None:
        """find_by_email retourne None si l'email est inconnu."""
        found = watcher_repo.find_by_email("absent@example.com")
        assert found is None

    def test_find_by_token_returns_watcher(
        self,
        watcher_repo: SqlAlchemyWatcherRepository,
        created_watcher: Watcher,
    ) -> None:
        """find_by_token retrouve un watcher existant."""
        found = watcher_repo.find_by_token(created_watcher.token)
        assert found is not None
        assert found.id == created_watcher.id

    def test_find_by_token_returns_none_if_absent(
        self, watcher_repo: SqlAlchemyWatcherRepository
    ) -> None:
        """find_by_token retourne None si le token est inconnu."""
        found = watcher_repo.find_by_token("not-a-valid-token")
        assert found is None

    def test_list_active_includes_new_watcher(
        self,
        watcher_repo: SqlAlchemyWatcherRepository,
        created_watcher: Watcher,
    ) -> None:
        """Un watcher actif apparaît dans list_active."""
        active = watcher_repo.list_active()
        ids = [w.id for w in active]
        assert created_watcher.id in ids


class TestWatchedDatasets:
    """Tests de gestion des datasets surveillés."""

    def test_add_watched_dataset(
        self,
        watcher_repo: SqlAlchemyWatcherRepository,
        created_watcher: Watcher,
    ) -> None:
        """add_watched_dataset ajoute une association watcher/dataset."""
        dataset_id = f"ds-{uuid.uuid4()}"
        result = watcher_repo.add_watched_dataset(
            watcher_id=created_watcher.id,
            dataset_id=dataset_id,
            last_known_resource_count=3,
        )

        try:
            assert isinstance(result, WatchedDataset)
            assert result.watcher_id == created_watcher.id
            assert result.dataset_id == dataset_id
            assert result.last_known_resource_count == 3
        finally:
            with SessionLocal() as session:
                session.query(WatchedDatasetModel).filter(
                    WatchedDatasetModel.id == result.id
                ).delete()
                session.commit()

    def test_add_watched_dataset_unique_constraint(
        self,
        watcher_repo: SqlAlchemyWatcherRepository,
        created_watcher: Watcher,
    ) -> None:
        """Ajouter deux fois le même dataset lève une ValueError."""
        dataset_id = f"ds-unique-{uuid.uuid4()}"
        first = watcher_repo.add_watched_dataset(
            watcher_id=created_watcher.id, dataset_id=dataset_id
        )

        try:
            with pytest.raises(ValueError):
                watcher_repo.add_watched_dataset(
                    watcher_id=created_watcher.id, dataset_id=dataset_id
                )
        finally:
            with SessionLocal() as session:
                session.query(WatchedDatasetModel).filter(
                    WatchedDatasetModel.id == first.id
                ).delete()
                session.commit()

    def test_find_by_dataset_returns_active_watchers(
        self,
        watcher_repo: SqlAlchemyWatcherRepository,
        created_watcher: Watcher,
    ) -> None:
        """find_by_dataset retourne les watchers actifs d'un dataset."""
        dataset_id = f"ds-find-{uuid.uuid4()}"
        watched = watcher_repo.add_watched_dataset(
            watcher_id=created_watcher.id, dataset_id=dataset_id
        )

        try:
            results = watcher_repo.find_by_dataset(dataset_id)
            ids = [w.id for w in results]
            assert created_watcher.id in ids
        finally:
            with SessionLocal() as session:
                session.query(WatchedDatasetModel).filter(
                    WatchedDatasetModel.id == watched.id
                ).delete()
                session.commit()

    def test_update_last_known(
        self,
        watcher_repo: SqlAlchemyWatcherRepository,
        created_watcher: Watcher,
    ) -> None:
        """update_last_known met à jour les valeurs connues d'un dataset."""
        dataset_id = f"ds-update-{uuid.uuid4()}"
        watched = watcher_repo.add_watched_dataset(
            watcher_id=created_watcher.id, dataset_id=dataset_id
        )

        try:
            watcher_repo.update_last_known(
                watcher_id=created_watcher.id,
                dataset_id=dataset_id,
                metadata_modified="2026-07-01T12:00:00+00:00",
                resource_count=5,
                quality_score=0.87,
            )
            with SessionLocal() as session:
                model = (
                    session.query(WatchedDatasetModel)
                    .filter(WatchedDatasetModel.id == watched.id)
                    .one()
                )
                assert model.last_known_metadata_modified == "2026-07-01T12:00:00+00:00"
                assert model.last_known_resource_count == 5
                assert model.last_known_quality_score == pytest.approx(0.87)
        finally:
            with SessionLocal() as session:
                session.query(WatchedDatasetModel).filter(
                    WatchedDatasetModel.id == watched.id
                ).delete()
                session.commit()

    def test_mark_and_find_last_alert_sent_at(
        self,
        watcher_repo: SqlAlchemyWatcherRepository,
        created_watcher: Watcher,
    ) -> None:
        """Le timestamp d'alerte est persiste par couple watcher+dataset."""
        dataset_id = f"ds-alert-sent-{uuid.uuid4()}"
        watched = watcher_repo.add_watched_dataset(
            watcher_id=created_watcher.id,
            dataset_id=dataset_id,
        )

        try:
            assert watcher_repo.find_last_alert_sent_at(created_watcher.id, dataset_id) is None

            sent_at = "2026-07-04T08:00:00+00:00"
            watcher_repo.mark_alert_sent(created_watcher.id, dataset_id, sent_at)
            assert watcher_repo.find_last_alert_sent_at(created_watcher.id, dataset_id) == sent_at
        finally:
            with SessionLocal() as session:
                session.query(WatchedDatasetModel).filter(
                    WatchedDatasetModel.id == watched.id
                ).delete()
                session.commit()


class TestChangeLogRepository:
    """Tests du journal des changements détectés."""

    def test_insert_returns_entry(self, changelog_repo: SqlAlchemyChangeLogRepository) -> None:
        """insert crée une entrée avec notified_at=None."""
        dataset_id = f"ds-cl-{uuid.uuid4()}"
        entry = changelog_repo.insert(
            dataset_id=dataset_id,
            change_type="metadata_modified",
            previous_value="2026-01-01",
            new_value="2026-07-01",
            detected_at=_iso_now(),
        )

        try:
            assert isinstance(entry, ChangeLogEntry)
            assert entry.dataset_id == dataset_id
            assert entry.change_type == "metadata_modified"
            assert entry.notified_at is None
        finally:
            with SessionLocal() as session:
                session.query(ChangeLogModel).filter(ChangeLogModel.id == entry.id).delete()
                session.commit()

    def test_find_unnotified_includes_new_entry(
        self, changelog_repo: SqlAlchemyChangeLogRepository
    ) -> None:
        """find_unnotified retourne les entrées sans notified_at."""
        dataset_id = f"ds-unnotified-{uuid.uuid4()}"
        entry = changelog_repo.insert(
            dataset_id=dataset_id,
            change_type="resource_count",
            previous_value="2",
            new_value="4",
            detected_at=_iso_now(),
        )

        try:
            unnotified = changelog_repo.find_unnotified()
            ids = [e.id for e in unnotified]
            assert entry.id in ids
        finally:
            with SessionLocal() as session:
                session.query(ChangeLogModel).filter(ChangeLogModel.id == entry.id).delete()
                session.commit()

    def test_mark_notified_sets_timestamp(
        self, changelog_repo: SqlAlchemyChangeLogRepository
    ) -> None:
        """mark_notified renseigne notified_at et sort l'entrée de find_unnotified."""
        dataset_id = f"ds-notified-{uuid.uuid4()}"
        entry = changelog_repo.insert(
            dataset_id=dataset_id,
            change_type="quality_score",
            previous_value="70",
            new_value="85",
            detected_at=_iso_now(),
        )

        try:
            notified_ts = _iso_now()
            changelog_repo.mark_notified(entry.id, notified_ts)

            unnotified_ids = [e.id for e in changelog_repo.find_unnotified()]
            assert entry.id not in unnotified_ids

            with SessionLocal() as session:
                model = session.query(ChangeLogModel).filter(ChangeLogModel.id == entry.id).one()
                assert model.notified_at == notified_ts
        finally:
            with SessionLocal() as session:
                session.query(ChangeLogModel).filter(ChangeLogModel.id == entry.id).delete()
                session.commit()

    def test_find_last_notified_at_returns_latest_timestamp(
        self, changelog_repo: SqlAlchemyChangeLogRepository
    ) -> None:
        """find_last_notified_at retourne l'horodatage le plus récent pour un dataset."""

        dataset_id = f"ds-last-notified-{uuid.uuid4()}"
        first = changelog_repo.insert(
            dataset_id=dataset_id,
            change_type="metadata_updated",
            previous_value="2026-01-01",
            new_value="2026-07-01",
            detected_at=_iso_now(),
        )
        second = changelog_repo.insert(
            dataset_id=dataset_id,
            change_type="resource_added",
            previous_value="1",
            new_value="2",
            detected_at=_iso_now(),
        )

        try:
            changelog_repo.mark_notified(first.id, "2026-07-02T08:00:00+00:00")
            changelog_repo.mark_notified(second.id, "2026-07-03T08:00:00+00:00")

            last_notified_at = changelog_repo.find_last_notified_at(dataset_id)
            assert last_notified_at == "2026-07-03T08:00:00+00:00"
        finally:
            with SessionLocal() as session:
                session.query(ChangeLogModel).filter(
                    ChangeLogModel.id.in_([first.id, second.id])
                ).delete(synchronize_session=False)
                session.commit()

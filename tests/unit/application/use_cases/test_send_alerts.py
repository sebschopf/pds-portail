"""Tests unitaires du use case SendAlertsUseCase."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from typing import Any
from uuid import UUID

import pytest

from app.application.ports.changelog_repository import ChangeLogEntry
from app.application.ports.magic_link_repository import MagicLink
from app.application.ports.watcher_repository import Watcher
from app.application.use_cases.send_alerts import SendAlertsUseCase
from app.core.config import Settings
from app.domain.cache_health import CacheCounts
from app.presentation.api.v1.schemas import (
    DatasetDetailResponse,
    DatasetStructure,
    ResourceResponse,
)


@dataclass
class _FakeCacheRepository:
    datasets: dict[str, DatasetDetailResponse]

    def get_dataset(self, dataset_id: str) -> DatasetDetailResponse | None:
        return self.datasets.get(dataset_id)

    def get_last_sync_timestamp(self) -> str | None:
        return None

    def get_cache_counts(self) -> CacheCounts:
        return CacheCounts(organizations=0, datasets=len(self.datasets), resources=0)


class _FakeWatcherRepository:
    def __init__(
        self,
        watchers_by_dataset: dict[str, list[Watcher]],
        last_alert_sent_at: Mapping[tuple[str, str], str | None],
    ) -> None:
        self._watchers_by_dataset = watchers_by_dataset
        self._last_alert_sent_at = dict(last_alert_sent_at)

    def create(
        self,
        email: str,
        token: str,
        plan: str = "monthly",
        polar_subscription_id: str | None = None,
    ) -> Watcher:
        _ = (email, token, plan, polar_subscription_id)
        raise NotImplementedError

    def find_by_email(self, email: str) -> Watcher | None:
        _ = email
        return None

    def find_by_token(self, token: str) -> Watcher | None:
        _ = token
        return None

    def find_by_polar_subscription_id(self, polar_subscription_id: str) -> Watcher | None:
        _ = polar_subscription_id
        return None

    def find_by_id(self, watcher_id: str) -> Watcher | None:
        _ = watcher_id
        return None

    def find_by_dataset(self, dataset_id: str) -> list[Watcher]:
        watchers = self._watchers_by_dataset.get(dataset_id, [])
        return [watcher for watcher in watchers if watcher.status == "active"]

    def list_active(self) -> list[Watcher]:
        return [
            watcher
            for watchers in self._watchers_by_dataset.values()
            for watcher in watchers
            if watcher.status == "active"
        ]

    def list_watched_datasets(self) -> list[Any]:
        return []

    def update_status(self, watcher_id: str, status: str) -> None:
        _ = (watcher_id, status)

    def add_watched_dataset(
        self,
        watcher_id: str,
        dataset_id: str,
        last_known_metadata_modified: str | None = None,
        last_known_resource_count: int | None = None,
        last_known_quality_score: float | None = None,
    ) -> Any:
        _ = (
            watcher_id,
            dataset_id,
            last_known_metadata_modified,
            last_known_resource_count,
            last_known_quality_score,
        )
        return None

    def remove_watched_dataset(self, watcher_id: str, dataset_id: str) -> None:
        _ = (watcher_id, dataset_id)

    def update_last_known(
        self,
        watcher_id: str,
        dataset_id: str,
        metadata_modified: str | None,
        resource_count: int | None,
        quality_score: float | None,
    ) -> None:
        _ = (watcher_id, dataset_id, metadata_modified, resource_count, quality_score)

    def find_last_alert_sent_at(self, watcher_id: str, dataset_id: str) -> str | None:
        return self._last_alert_sent_at.get((watcher_id, dataset_id))

    def mark_alert_sent(self, watcher_id: str, dataset_id: str, sent_at: str) -> None:
        self._last_alert_sent_at[(watcher_id, dataset_id)] = sent_at


class _FakeChangeLogRepository:
    def __init__(
        self, entries: list[ChangeLogEntry], last_notified_at: Mapping[str, str | None]
    ) -> None:
        self.entries = entries
        self.last_notified_at = dict(last_notified_at)
        self.notified_calls: list[tuple[str, str]] = []

    def insert(
        self,
        dataset_id: str,
        change_type: str,
        previous_value: str | None,
        new_value: str | None,
        detected_at: str,
    ) -> ChangeLogEntry:
        entry = ChangeLogEntry(
            id=f"change-{len(self.entries) + 1}",
            dataset_id=dataset_id,
            change_type=change_type,
            previous_value=previous_value,
            new_value=new_value,
            detected_at=detected_at,
            notified_at=None,
        )
        self.entries.append(entry)
        return entry

    def find_unnotified(self) -> list[ChangeLogEntry]:
        return [entry for entry in self.entries if entry.notified_at is None]

    def find_last_notified_at(self, dataset_id: str) -> str | None:
        return self.last_notified_at.get(dataset_id)

    def mark_notified(self, entry_id: str, notified_at: str) -> None:
        self.notified_calls.append((entry_id, notified_at))
        self.entries = [
            entry if entry.id != entry_id else entry._replace(notified_at=notified_at)
            for entry in self.entries
        ]
        dataset_id = next(entry.dataset_id for entry in self.entries if entry.id == entry_id)
        self.last_notified_at[dataset_id] = notified_at


class _FakeMagicLinkRepository:
    def __init__(self) -> None:
        self.created_links: list[MagicLink] = []
        self.create_calls: list[dict[str, str]] = []

    def create(
        self,
        watcher_id: str,
        token_hash: str,
        created_at: str,
        expires_at: str,
    ) -> MagicLink:
        self.create_calls.append(
            {
                "watcher_id": watcher_id,
                "token_hash": token_hash,
                "created_at": created_at,
                "expires_at": expires_at,
            }
        )
        link = MagicLink(
            id=f"magic-link-{len(self.create_calls)}",
            watcher_id=watcher_id,
            token_hash=token_hash,
            created_at=created_at,
            expires_at=expires_at,
            used_at=None,
        )
        self.created_links.append(link)
        return link

    def find_by_token_hash(self, token_hash: str) -> MagicLink | None:
        for link in self.created_links:
            if link.token_hash == token_hash:
                return link
        return None

    def mark_used(self, magic_link_id: str, used_at: str) -> None:
        self.created_links = [
            link if link.id != magic_link_id else link._replace(used_at=used_at)
            for link in self.created_links
        ]


class _FakeSMTP:
    instances: list[_FakeSMTP] = []

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.started_tls = False
        self.login_args: tuple[str, str] | None = None
        self.sent_messages: list[EmailMessage] = []
        self.__class__.instances.append(self)

    def __enter__(self) -> _FakeSMTP:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: Any,
    ) -> None:
        _ = (exc_type, exc, traceback)
        return None

    def starttls(self, context: Any) -> None:
        _ = context
        self.started_tls = True

    def login(self, username: str, password: str) -> None:
        self.login_args = (username, password)

    def send_message(self, message: EmailMessage) -> None:
        self.sent_messages.append(message)


@pytest.fixture(autouse=True)
def _reset_fake_smtp(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeSMTP.instances = []
    monkeypatch.setattr("app.application.use_cases.send_alerts.smtplib.SMTP", _FakeSMTP)
    _ = _reset_fake_smtp


@pytest.fixture
def fixed_now() -> datetime:
    return datetime(2026, 7, 3, 12, 0, tzinfo=UTC)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_user="smtp-user",
        smtp_password="smtp-password",
        smtp_from="alerts@example.com",
        smtp_daily_limit=50,
    )


@pytest.fixture
def dataset_detail() -> DatasetDetailResponse:
    return DatasetDetailResponse(
        id="dataset-1",
        title="Dataset 1",
        description="Description",
        org_id="org-1",
        org_name="Org 1",
        created="2026-06-01T00:00:00+00:00",
        modified="2026-07-03T11:00:00+00:00",
        quality_score=82,
        completeness=90,
        freshness_days=1,
        dataset_structure=DatasetStructure(
            fields=[],
            formats=["CSV"],
            update_frequency=None,
            last_updated=None,
        ),
        access_modes=[],
        resources=[
            ResourceResponse(
                id="res-1",
                name="Resource 1",
                format="CSV",
                url="https://example.com/resource.csv",
            )
        ],
        tags=["open-data"],
        ckan_url=None,
    )


@pytest.fixture
def active_watcher() -> Watcher:
    return Watcher(
        id="watcher-active",
        email="active@example.com",
        polar_subscription_id=None,
        plan="monthly",
        status="active",
        token="permanent-token-active",
        created_at="2026-07-01T00:00:00+00:00",
        updated_at="2026-07-01T00:00:00+00:00",
    )


@pytest.fixture
def suspended_watcher() -> Watcher:
    return Watcher(
        id="watcher-suspended",
        email="suspended@example.com",
        polar_subscription_id=None,
        plan="monthly",
        status="suspended",
        token="permanent-token-suspended",
        created_at="2026-07-01T00:00:00+00:00",
        updated_at="2026-07-01T00:00:00+00:00",
    )


def _build_use_case(
    entries: list[ChangeLogEntry],
    watchers_by_dataset: dict[str, list[Watcher]],
    last_notified_at: Mapping[str, str | None],
    last_alert_sent_at: Mapping[tuple[str, str], str | None],
    dataset_detail: DatasetDetailResponse,
    settings: Settings,
    fixed_now: datetime,
) -> tuple[SendAlertsUseCase, _FakeChangeLogRepository, _FakeMagicLinkRepository]:
    cache_repository = _FakeCacheRepository(datasets={dataset_detail.id: dataset_detail})
    watcher_repository = _FakeWatcherRepository(
        watchers_by_dataset=watchers_by_dataset,
        last_alert_sent_at=last_alert_sent_at,
    )
    changelog_repository = _FakeChangeLogRepository(
        entries=entries,
        last_notified_at=last_notified_at,
    )
    magic_link_repository = _FakeMagicLinkRepository()

    use_case = SendAlertsUseCase(
        change_log_repository=changelog_repository,
        watcher_repository=watcher_repository,
        cache_repository=cache_repository,
        magic_link_repository=magic_link_repository,
        settings=settings,
        now_provider=lambda: fixed_now,
    )
    return use_case, changelog_repository, magic_link_repository


def test_send_alerts_sends_email_with_magic_link_and_unsubscribe(
    dataset_detail: DatasetDetailResponse,
    active_watcher: Watcher,
    settings: Settings,
    fixed_now: datetime,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Un email d'alerte contient le magic link temporaire et les champs attendus."""

    monkeypatch.setattr(
        "app.application.use_cases.send_alerts.uuid.uuid4",
        lambda: UUID("12345678-1234-5678-1234-567812345678"),
    )
    entries = [
        ChangeLogEntry(
            id="change-1",
            dataset_id=dataset_detail.id,
            change_type="metadata_updated",
            previous_value="2026-06-01T00:00:00+00:00",
            new_value=dataset_detail.modified,
            detected_at=fixed_now.isoformat(),
            notified_at=None,
        )
    ]

    use_case, changelog_repository, magic_link_repository = _build_use_case(
        entries=entries,
        watchers_by_dataset={dataset_detail.id: [active_watcher]},
        last_notified_at={},
        last_alert_sent_at={},
        dataset_detail=dataset_detail,
        settings=settings,
        fixed_now=fixed_now,
    )

    result = use_case.execute()

    assert result["emails_sent"] == 1
    assert result["datasets_processed"] == 1
    assert len(_FakeSMTP.instances) == 1
    assert len(_FakeSMTP.instances[0].sent_messages) == 1
    assert len(magic_link_repository.create_calls) == 1
    assert len(changelog_repository.notified_calls) == 1

    sent_message = _FakeSMTP.instances[0].sent_messages[0]
    plain_part = sent_message.get_body(preferencelist=("plain",))
    html_part = sent_message.get_body(preferencelist=("html",))
    assert plain_part is not None
    assert html_part is not None
    plain_body = plain_part.get_content()
    html_body = html_part.get_content()

    assert sent_message["Subject"] == "[PDS-Portail] Changement détecté : Dataset 1"
    assert sent_message["From"] == "alerts@example.com"
    assert sent_message["To"] == "active@example.com"
    magic_url = "https://pds-portail.vercel.app/alertes?magic=12345678-1234-5678-1234-567812345678"
    assert magic_url in plain_body
    assert magic_url in html_body
    assert "permanent-token-active" not in sent_message.as_string()
    assert "Dataset 1" in plain_body
    assert "Dernière mise à jour modifiée" in plain_body
    assert magic_link_repository.create_calls[0]["created_at"] == fixed_now.isoformat()
    assert (
        magic_link_repository.create_calls[0]["expires_at"]
        == (fixed_now + timedelta(minutes=15)).isoformat()
    )


def test_send_alerts_ignores_suspended_watchers(
    dataset_detail: DatasetDetailResponse,
    active_watcher: Watcher,
    suspended_watcher: Watcher,
    settings: Settings,
    fixed_now: datetime,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Seuls les watchers actifs reçoivent les alertes."""

    monkeypatch.setattr(
        "app.application.use_cases.send_alerts.uuid.uuid4",
        lambda: UUID("12345678-1234-5678-1234-567812345678"),
    )
    entries = [
        ChangeLogEntry(
            id="change-1",
            dataset_id=dataset_detail.id,
            change_type="resource_added",
            previous_value="1",
            new_value="2",
            detected_at=fixed_now.isoformat(),
            notified_at=None,
        )
    ]

    use_case, _, _ = _build_use_case(
        entries=entries,
        watchers_by_dataset={dataset_detail.id: [active_watcher, suspended_watcher]},
        last_notified_at={},
        last_alert_sent_at={},
        dataset_detail=dataset_detail,
        settings=settings,
        fixed_now=fixed_now,
    )

    result = use_case.execute()

    assert result["emails_sent"] == 1
    assert len(_FakeSMTP.instances) == 1
    assert len(_FakeSMTP.instances[0].sent_messages) == 1


def test_send_alerts_skips_dataset_notified_within_24h(
    dataset_detail: DatasetDetailResponse,
    active_watcher: Watcher,
    settings: Settings,
    fixed_now: datetime,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Un dataset déjà notifié dans les 24h est ignoré."""

    monkeypatch.setattr(
        "app.application.use_cases.send_alerts.uuid.uuid4",
        lambda: UUID("12345678-1234-5678-1234-567812345678"),
    )
    entries = [
        ChangeLogEntry(
            id="change-1",
            dataset_id=dataset_detail.id,
            change_type="quality_degraded",
            previous_value="90",
            new_value="82",
            detected_at=fixed_now.isoformat(),
            notified_at=None,
        )
    ]
    last_alert_sent_at = {
        (active_watcher.id, dataset_detail.id): (fixed_now - timedelta(hours=1)).isoformat()
    }

    use_case, changelog_repository, _ = _build_use_case(
        entries=entries,
        watchers_by_dataset={dataset_detail.id: [active_watcher]},
        last_notified_at={},
        last_alert_sent_at=last_alert_sent_at,
        dataset_detail=dataset_detail,
        settings=settings,
        fixed_now=fixed_now,
    )

    result = use_case.execute()

    assert result["emails_sent"] == 0
    assert result["skipped_rate_limited"] == 1
    assert _FakeSMTP.instances == []
    assert changelog_repository.notified_calls == []


def test_send_alerts_groups_multiple_changes_single_email(
    dataset_detail: DatasetDetailResponse,
    active_watcher: Watcher,
    settings: Settings,
    fixed_now: datetime,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Plusieurs changements d'un même dataset déclenchent un seul email."""

    monkeypatch.setattr(
        "app.application.use_cases.send_alerts.uuid.uuid4",
        lambda: UUID("12345678-1234-5678-1234-567812345678"),
    )
    entries = [
        ChangeLogEntry(
            id="change-1",
            dataset_id=dataset_detail.id,
            change_type="metadata_updated",
            previous_value="2026-06-01T00:00:00+00:00",
            new_value=dataset_detail.modified,
            detected_at=fixed_now.isoformat(),
            notified_at=None,
        ),
        ChangeLogEntry(
            id="change-2",
            dataset_id=dataset_detail.id,
            change_type="resource_added",
            previous_value="1",
            new_value="2",
            detected_at=fixed_now.isoformat(),
            notified_at=None,
        ),
    ]

    use_case, _, _ = _build_use_case(
        entries=entries,
        watchers_by_dataset={dataset_detail.id: [active_watcher]},
        last_notified_at={},
        last_alert_sent_at={},
        dataset_detail=dataset_detail,
        settings=settings,
        fixed_now=fixed_now,
    )

    result = use_case.execute()

    assert result["emails_sent"] == 1
    assert len(_FakeSMTP.instances[0].sent_messages) == 1
    plain_part = _FakeSMTP.instances[0].sent_messages[0].get_body(preferencelist=("plain",))
    assert plain_part is not None
    plain_body = plain_part.get_content()
    assert "Dernière mise à jour modifiée" in plain_body
    assert "Nouvelle ressource ajoutée" in plain_body


def test_send_alerts_stops_at_daily_limit(
    dataset_detail: DatasetDetailResponse,
    active_watcher: Watcher,
    settings: Settings,
    fixed_now: datetime,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """La limite quotidienne borne le nombre d'emails envoyés."""

    monkeypatch.setattr(
        "app.application.use_cases.send_alerts.uuid.uuid4",
        lambda: UUID("12345678-1234-5678-1234-567812345678"),
    )
    second_dataset = dataset_detail.model_copy(update={"id": "dataset-2", "title": "Dataset 2"})
    entries = [
        ChangeLogEntry(
            id="change-1",
            dataset_id=dataset_detail.id,
            change_type="metadata_updated",
            previous_value=None,
            new_value=dataset_detail.modified,
            detected_at=fixed_now.isoformat(),
            notified_at=None,
        ),
        ChangeLogEntry(
            id="change-2",
            dataset_id=second_dataset.id,
            change_type="metadata_updated",
            previous_value=None,
            new_value=second_dataset.modified,
            detected_at=fixed_now.isoformat(),
            notified_at=None,
        ),
    ]
    limited_settings = settings.model_copy(update={"smtp_daily_limit": 1})

    use_case, changelog_repository, _ = _build_use_case(
        entries=entries,
        watchers_by_dataset={
            dataset_detail.id: [active_watcher],
            second_dataset.id: [active_watcher],
        },
        last_notified_at={},
        last_alert_sent_at={},
        dataset_detail=dataset_detail,
        settings=limited_settings,
        fixed_now=fixed_now,
    )

    result = use_case.execute()

    assert result["emails_sent"] == 1
    assert len(_FakeSMTP.instances[0].sent_messages) == 1
    assert len(changelog_repository.notified_calls) == 1

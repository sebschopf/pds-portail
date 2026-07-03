"""Cas d'usage d'envoi d'alertes email pour les changements détectés."""

from __future__ import annotations

import hashlib
import logging
import smtplib
import ssl
import uuid
from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from pathlib import Path

from app.application.ports.cache_read_repository import CacheReadRepositoryPort
from app.application.ports.changelog_repository import ChangeLogEntry, ChangeLogRepositoryPort
from app.application.ports.magic_link_repository import MagicLinkRepositoryPort
from app.application.ports.watcher_repository import Watcher, WatcherRepositoryPort
from app.core.config import Settings
from app.presentation.api.v1.schemas import DatasetDetailResponse

logger = logging.getLogger(__name__)

_ALERT_TTL_MINUTES = 15
_RATE_LIMIT_WINDOW = timedelta(hours=24)
_PUBLIC_FRONTEND_BASE_URL = "https://pds-portail.vercel.app"
_TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "infrastructure" / "email"


class SendAlertsUseCase:
    """Construit et envoie les emails d'alerte aux watchers actifs."""

    def __init__(
        self,
        change_log_repository: ChangeLogRepositoryPort,
        watcher_repository: WatcherRepositoryPort,
        cache_repository: CacheReadRepositoryPort,
        magic_link_repository: MagicLinkRepositoryPort,
        settings: Settings,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self._change_log_repository = change_log_repository
        self._watcher_repository = watcher_repository
        self._cache_repository = cache_repository
        self._magic_link_repository = magic_link_repository
        self._settings = settings
        self._now_provider = now_provider or (lambda: datetime.now(UTC))

    def execute(self) -> dict[str, int]:
        """Envoie les emails en attente et marque les changements traités."""

        # SPEC-009 §3.1: seules les entrées non notifiées sont candidates à l'envoi.
        pending_entries = self._change_log_repository.find_unnotified()
        grouped_entries = self._group_entries_by_dataset(pending_entries)

        datasets_processed = 0
        emails_sent = 0
        skipped_rate_limited = 0
        skipped_missing_dataset = 0

        for dataset_id, entries in grouped_entries.items():
            if emails_sent >= self._settings.smtp_daily_limit:
                logger.info("Limite quotidienne SMTP atteinte: %s", self._settings.smtp_daily_limit)
                break

            if self._is_rate_limited(dataset_id):
                skipped_rate_limited += 1
                continue

            dataset = self._cache_repository.get_dataset(dataset_id)
            if dataset is None:
                skipped_missing_dataset += 1
                continue

            watchers = self._watcher_repository.find_by_dataset(dataset_id)
            if not watchers:
                self._mark_entries_notified(entries)
                datasets_processed += 1
                continue

            for watcher in watchers:
                if emails_sent >= self._settings.smtp_daily_limit:
                    break
                # ADR-030: le token permanent watcher.token ne doit jamais quitter le backend.
                # On émet donc un magic link temporaire dédié à cet email d'alerte.
                magic_link_token = self._issue_magic_link(watcher)
                message = self._build_email_message(
                    watcher=watcher,
                    dataset=dataset,
                    entries=entries,
                    magic_link_token=magic_link_token,
                )
                self._send_message(message)
                emails_sent += 1

            self._mark_entries_notified(entries)
            datasets_processed += 1

        return {
            "datasets_processed": datasets_processed,
            "emails_sent": emails_sent,
            "skipped_rate_limited": skipped_rate_limited,
            "skipped_missing_dataset": skipped_missing_dataset,
        }

    def _group_entries_by_dataset(
        self, entries: list[ChangeLogEntry]
    ) -> dict[str, list[ChangeLogEntry]]:
        grouped: dict[str, list[ChangeLogEntry]] = defaultdict(list)
        for entry in entries:
            grouped[entry.dataset_id].append(entry)
        return dict(grouped)

    def _is_rate_limited(self, dataset_id: str) -> bool:
        # SPEC-009 / ADR-029: pas plus d'un email d'alerte par dataset sur 24h.
        last_notified_at = self._change_log_repository.find_last_notified_at(dataset_id)
        if last_notified_at is None:
            return False
        last_notified = self._parse_iso_datetime(last_notified_at)
        return self._now_provider() - last_notified < _RATE_LIMIT_WINDOW

    def _issue_magic_link(self, watcher: Watcher) -> str:
        # ADR-030: le token brut est UUID v4, seul son hash SHA-256 est persisté.
        token = str(uuid.uuid4())
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        now = self._now_provider()
        expires_at = now + timedelta(minutes=_ALERT_TTL_MINUTES)
        self._magic_link_repository.create(
            watcher_id=watcher.id,
            token_hash=token_hash,
            created_at=now.isoformat(),
            expires_at=expires_at.isoformat(),
        )
        return token

    def _build_email_message(
        self,
        watcher: Watcher,
        dataset: DatasetDetailResponse,
        entries: list[ChangeLogEntry],
        magic_link_token: str,
    ) -> EmailMessage:
        change_descriptions = [self._describe_change(entry.change_type) for entry in entries]
        alerts_link = f"{_PUBLIC_FRONTEND_BASE_URL}/alertes?magic={magic_link_token}"
        dataset_link = f"{_PUBLIC_FRONTEND_BASE_URL}/dataset/{dataset.id}"
        quality_score = "N/A" if dataset.quality_score is None else str(dataset.quality_score)

        context: dict[str, str] = {
            "dataset_title": dataset.title,
            "dataset_link": dataset_link,
            "alerts_link": alerts_link,
            "unsubscribe_link": alerts_link,
            "quality_score": quality_score,
            "change_title": ", ".join(change_descriptions),
            "change_bullets_html": "".join(f"<li>{item}</li>" for item in change_descriptions),
            "change_bullets_text": "\n".join(f"- {item}" for item in change_descriptions),
        }

        subject = f"[PDS-Portail] Changement détecté : {dataset.title}"
        html_template = self._load_template("alert_email.html")
        text_template = self._load_template("alert_email.txt")

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self._require_smtp_from()
        message["To"] = watcher.email
        message.set_content(self._render(text_template, context))
        message.add_alternative(self._render(html_template, context), subtype="html")
        return message

    def _send_message(self, message: EmailMessage) -> None:
        # ADR-029: transport SMTP standard (STARTTLS) sans dépendance externe supplémentaire.
        host = self._require_smtp_host()
        if self._settings.smtp_user is None or self._settings.smtp_password is None:
            raise RuntimeError("SMTP_USER et SMTP_PASSWORD doivent être configurés.")

        with smtplib.SMTP(host, self._settings.smtp_port) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(self._settings.smtp_user, self._settings.smtp_password)
            server.send_message(message)

    def _mark_entries_notified(self, entries: list[ChangeLogEntry]) -> None:
        notified_at = self._now_provider().isoformat()
        for entry in entries:
            self._change_log_repository.mark_notified(entry.id, notified_at)

    def _load_template(self, template_name: str) -> str:
        return (_TEMPLATE_DIR / template_name).read_text(encoding="utf-8")

    def _render(self, template: str, context: dict[str, str]) -> str:
        return template.format(**context)

    def _parse_iso_datetime(self, value: str) -> datetime:
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)

    def _describe_change(self, change_type: str) -> str:
        mapping = {
            "metadata_updated": "Dernière mise à jour modifiée",
            "resource_added": "Nouvelle ressource ajoutée",
            "resource_removed": "Ressource supprimée",
            "quality_degraded": "Score qualité dégradé",
            "link_broken": "Lien de ressource cassé",
        }
        return mapping.get(change_type, change_type)

    def _require_smtp_host(self) -> str:
        if self._settings.smtp_host is None:
            raise RuntimeError("SMTP_HOST doit être configuré.")
        return self._settings.smtp_host

    def _require_smtp_from(self) -> str:
        if self._settings.smtp_from is None:
            raise RuntimeError("SMTP_FROM doit être configuré.")
        return self._settings.smtp_from

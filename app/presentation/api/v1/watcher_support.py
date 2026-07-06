import logging
import smtplib
import ssl
import uuid
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from hashlib import sha256
from pathlib import Path

from app.application.ports.watcher_repository import Watcher
from app.infrastructure.persistence.database import SessionLocal
from app.infrastructure.persistence.magic_link_repository import SqlAlchemyMagicLinkRepository
from app.infrastructure.persistence.models import (
    SupportAuditModel,
    SupportEmailEventModel,
    SupportWebhookEventModel,
)
from app.presentation.api.v1.schemas import DatasetDetailResponse

logger = logging.getLogger(__name__)


def support_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def redact_email(email: str) -> str:
    normalized = email.strip().lower().encode("utf-8")
    return sha256(normalized).hexdigest()[:12]


def mask_identifier(value: str | None) -> str | None:
    if value is None:
        return None
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}…{value[-4:]}"


def audit_internal_support_event(
    *,
    route: str,
    method: str,
    outcome: str,
    operator_id: str,
    watcher_id: str | None = None,
    email: str | None = None,
    request_id: str | None = None,
    reason: str | None = None,
) -> str:
    audit_id = str(uuid.uuid4())
    with SessionLocal() as session:
        session.add(
            SupportAuditModel(
                id=audit_id,
                timestamp=support_now_iso(),
                route=route,
                method=method,
                outcome=outcome,
                operator_id=operator_id,
                watcher_id=watcher_id,
                email_hash_prefix=redact_email(email) if email else None,
                request_id=request_id,
                reason=reason,
            )
        )
        session.commit()
    return audit_id


def record_support_webhook_event(
    *,
    watcher_id: str | None,
    event_type: str,
    delivery_status: str,
    correlation_id: str | None,
) -> None:
    with SessionLocal() as session:
        session.add(
            SupportWebhookEventModel(
                id=str(uuid.uuid4()),
                watcher_id=watcher_id,
                event_type=event_type,
                received_at=support_now_iso(),
                delivery_status=delivery_status,
                correlation_id=correlation_id,
            )
        )
        session.commit()


def record_support_email_event(
    *,
    watcher_id: str,
    email_kind: str,
    status: str,
    provider_message_id_masked: str | None = None,
    error_code: str | None = None,
) -> None:
    with SessionLocal() as session:
        session.add(
            SupportEmailEventModel(
                id=str(uuid.uuid4()),
                watcher_id=watcher_id,
                email_kind=email_kind,
                status=status,
                created_at=support_now_iso(),
                provider_message_id_masked=provider_message_id_masked,
                error_code=error_code,
            )
        )
        session.commit()


def issue_magic_link_for_watcher(watcher_id: str) -> tuple[str, str]:
    token = str(uuid.uuid4())
    token_hash = sha256(token.encode("utf-8")).hexdigest()
    issued_at = datetime.now(UTC)
    expires_at = issued_at + timedelta(minutes=15)

    magic_link_repo = SqlAlchemyMagicLinkRepository()
    magic_link_repo.create(
        watcher_id=watcher_id,
        token_hash=token_hash,
        created_at=issued_at.isoformat(),
        expires_at=expires_at.isoformat(),
    )
    return token, issued_at.isoformat()


def dispatch_magic_link_email(
    *,
    watcher: Watcher,
    subject: str,
    template_name: str,
    email_kind: str,
    template_context: dict[str, str],
    smtp_host: str | None,
    smtp_port: int,
    smtp_user: str | None,
    smtp_password: str | None,
    smtp_from: str | None,
) -> str:
    email_hash_prefix = redact_email(watcher.email)

    if not smtp_host or not smtp_user or not smtp_password or not smtp_from:
        logger.warning(
            "SMTP incomplet pour support email watcher=%s email_hash=%s",
            watcher.id,
            email_hash_prefix,
        )
        record_support_email_event(
            watcher_id=watcher.id,
            email_kind=email_kind,
            status="queued",
            error_code="smtp_missing",
        )
        return "queued"

    template_dir = Path(__file__).resolve().parents[3] / "infrastructure" / "email"
    html_template_path = template_dir / f"{template_name}.html"
    text_template_path = template_dir / f"{template_name}.txt"

    if not html_template_path.exists() or not text_template_path.exists():
        logger.warning(
            "Templates email manquants pour support watcher=%s template=%s email_hash=%s",
            watcher.id,
            template_name,
            email_hash_prefix,
        )
        record_support_email_event(
            watcher_id=watcher.id,
            email_kind=email_kind,
            status="queued",
            error_code="template_missing",
        )
        return "queued"

    try:
        html_body = html_template_path.read_text(encoding="utf-8").format(**template_context)
        text_body = text_template_path.read_text(encoding="utf-8").format(**template_context)

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = smtp_from
        message["To"] = watcher.email
        message.set_content(text_body)
        message.add_alternative(html_body, subtype="html")

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(smtp_user, smtp_password)
            server.send_message(message)

        record_support_email_event(
            watcher_id=watcher.id,
            email_kind=email_kind,
            status="sent",
        )
        return "sent"
    except Exception as exc:
        logger.error(
            "Erreur envoi email support watcher=%s email_hash=%s: %s",
            watcher.id,
            email_hash_prefix,
            exc,
            exc_info=True,
        )
        record_support_email_event(
            watcher_id=watcher.id,
            email_kind=email_kind,
            status="failed",
            error_code=type(exc).__name__,
        )
        return "failed"


def send_welcome_email_for_watcher(
    watcher: Watcher,
    dataset: DatasetDetailResponse,
    smtp_host: str | None,
    smtp_port: int,
    smtp_user: str | None,
    smtp_password: str | None,
    smtp_from: str | None,
) -> None:
    """Envoie un email de bienvenue avec magic link après inscription Polar (PDS-90)."""
    email_hash_prefix = redact_email(watcher.email)

    if not smtp_host or not smtp_user or not smtp_password or not smtp_from:
        logger.warning(
            "Impossible d'envoyer email bienvenue pour watcher=%s email_hash=%s: "
            "config SMTP incomplète",
            watcher.id,
            email_hash_prefix,
        )
        record_support_email_event(
            watcher_id=watcher.id,
            email_kind="welcome",
            status="queued",
            error_code="smtp_missing",
        )
        return

    try:
        token = str(uuid.uuid4())
        token_hash = sha256(token.encode("utf-8")).hexdigest()
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=15)

        magic_link_repo = SqlAlchemyMagicLinkRepository()
        magic_link_repo.create(
            watcher_id=watcher.id,
            token_hash=token_hash,
            created_at=now.isoformat(),
            expires_at=expires_at.isoformat(),
        )

        alerts_link = f"https://pds-portail.ch/alertes?magic={token}"
        dataset_link = f"https://pds-portail.ch/dataset/{dataset.id}"

        template_dir = Path(__file__).resolve().parents[3] / "infrastructure" / "email"
        html_template_path = template_dir / "welcome_email.html"
        text_template_path = template_dir / "welcome_email.txt"

        if not html_template_path.exists() or not text_template_path.exists():
            logger.warning(
                "Templates email bienvenue manquants pour watcher=%s email_hash=%s: %s, %s",
                watcher.id,
                email_hash_prefix,
                html_template_path,
                text_template_path,
            )
            record_support_email_event(
                watcher_id=watcher.id,
                email_kind="welcome",
                status="queued",
                error_code="template_missing",
            )
            return

        html_content = html_template_path.read_text(encoding="utf-8")
        text_content = text_template_path.read_text(encoding="utf-8")

        context = {
            "dataset_title": dataset.title,
            "alerts_link": alerts_link,
            "dataset_link": dataset_link,
        }

        html_body = html_content.format(**context)
        text_body = text_content.format(**context)

        message = EmailMessage()
        message["Subject"] = f"[PDS-Portail] Bienvenue ! Surveillance activée pour {dataset.title}"
        message["From"] = smtp_from
        message["To"] = watcher.email
        message.set_content(text_body)
        message.add_alternative(html_body, subtype="html")

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(smtp_user, smtp_password)
            server.send_message(message)

        logger.info(
            "Email bienvenue envoyé pour watcher=%s email_hash=%s dataset=%s",
            watcher.id,
            email_hash_prefix,
            dataset.id,
        )
        record_support_email_event(
            watcher_id=watcher.id,
            email_kind="welcome",
            status="sent",
        )
    except Exception as exc:
        logger.error(
            "Erreur lors de l'envoi de l'email bienvenue watcher=%s email_hash=%s: %s",
            watcher.id,
            email_hash_prefix,
            exc,
            exc_info=True,
        )
        record_support_email_event(
            watcher_id=watcher.id,
            email_kind="welcome",
            status="failed",
            error_code=type(exc).__name__,
        )

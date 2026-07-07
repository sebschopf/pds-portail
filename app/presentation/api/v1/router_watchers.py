import logging
import uuid
from contextlib import suppress
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, cast

from fastapi import APIRouter, Header, HTTPException, Query, Request, Response

from app.application.ports.watcher_repository import Watcher
from app.application.use_cases.get_dataset_detail import GetDatasetDetailUseCase
from app.infrastructure.persistence.database import SessionLocal
from app.infrastructure.persistence.dataset_detail_adapter import SqlAlchemyDatasetDetailAdapter
from app.infrastructure.persistence.magic_link_repository import SqlAlchemyMagicLinkRepository
from app.infrastructure.persistence.models import ChangeLogModel
from app.infrastructure.persistence.watcher_repository import SqlAlchemyWatcherRepository
from app.presentation.api.v1.schemas import (
    AlertItemResponse,
    AlertsResponse,
    MagicLinkConsumeResponse,
    MagicLinkRequestBody,
    WatchedDatasetItemResponse,
    WatcherCreateRequest,
    WatcherCreateResponse,
    WatchersListResponse,
)
from app.presentation.api.v1.watcher_support import (
    dispatch_magic_link_email as _dispatch_magic_link_email,
)
from app.presentation.api.v1.watcher_support import (
    issue_magic_link_for_watcher as _issue_magic_link_for_watcher,
)
from app.presentation.api.v1.watcher_support import (
    record_support_webhook_event as _record_support_webhook_event,
)
from app.presentation.api.v1.watcher_support import (
    send_welcome_email_for_watcher as _send_welcome_email_for_watcher,
)
from app.presentation.api.v1.webhooks import (
    PolarWebhookEvent,
    WebhookVerificationError,
    verify_polar_webhook,
)

logger = logging.getLogger(__name__)
watchers_router = APIRouter()


def _require_watcher_by_token(token: str) -> tuple[SqlAlchemyWatcherRepository, Watcher]:
    """Valide le token watcher et retourne (repo, watcher) ou 401."""
    try:
        uuid.UUID(token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc

    watcher_repo = SqlAlchemyWatcherRepository()
    watcher = watcher_repo.find_by_token(token)
    if watcher is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return watcher_repo, watcher


@watchers_router.post("/webhooks/polar")
async def webhook_polar(
    request: Request,
    x_polar_signature: str | None = Header(None, alias="X-Polar-Signature"),
) -> dict[str, str]:
    """Endpoint public Polar : vérifie signature puis traite l'événement métier."""

    from app.core.config import get_settings

    settings = get_settings()
    if not settings.polar_webhook_secret:
        raise HTTPException(status_code=503, detail="POLAR_WEBHOOK_SECRET not configured")
    if not x_polar_signature:
        raise HTTPException(status_code=401, detail="Missing X-Polar-Signature header")

    raw_body = await request.body()
    try:
        payload = await request.json()
        event = PolarWebhookEvent(**payload)
        verify_polar_webhook(
            body=raw_body,
            signature_header=x_polar_signature,
            secret=settings.polar_webhook_secret,
            timestamp=event.timestamp,
        )
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid webhook payload") from exc
    except WebhookVerificationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    watcher_repo = SqlAlchemyWatcherRepository()

    if event.type == "order.created":
        customer_email = str(event.data.get("customer_email", "")).strip()
        metadata_raw = event.data.get("metadata")
        metadata: dict[str, Any] = (
            cast(dict[str, Any], metadata_raw) if isinstance(metadata_raw, dict) else {}
        )
        dataset_id = str(metadata.get("dataset_id", "")).strip()
        polar_subscription_id = (
            str(event.data.get("subscription_id")).strip()
            if event.data.get("subscription_id") is not None
            else None
        )
        if not customer_email or not dataset_id:
            raise HTTPException(
                status_code=400,
                detail="order.created requires customer_email and metadata.dataset_id",
            )

        detail = GetDatasetDetailUseCase(SqlAlchemyDatasetDetailAdapter()).execute(dataset_id)
        if detail is None:
            raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")

        watcher = watcher_repo.find_by_email(customer_email)
        if watcher is None:
            watcher = watcher_repo.create(
                email=customer_email,
                token=str(uuid.uuid4()),
                polar_subscription_id=polar_subscription_id,
            )
        else:
            if polar_subscription_id and watcher.polar_subscription_id != polar_subscription_id:
                watcher_repo.update_subscription(watcher.id, polar_subscription_id)
            if watcher.status != "active":
                watcher_repo.update_status(watcher.id, "active")
            watcher = watcher_repo.find_by_email(customer_email) or watcher

        with suppress(ValueError):
            watcher_repo.add_watched_dataset(
                watcher_id=watcher.id,
                dataset_id=dataset_id,
                last_known_metadata_modified=detail.modified,
                last_known_resource_count=len(detail.resources),
                last_known_quality_score=(
                    float(detail.quality_score) if detail.quality_score is not None else None
                ),
            )

        try:
            _send_welcome_email_for_watcher(
                watcher,
                detail,
                smtp_host=settings.smtp_host,
                smtp_port=settings.smtp_port,
                smtp_user=settings.smtp_user,
                smtp_password=settings.smtp_password,
                smtp_from=settings.smtp_from,
            )
        except Exception as exc:
            logger.warning("Erreur email bienvenue (webhook continue): %s", exc)

        _record_support_webhook_event(
            watcher_id=watcher.id,
            event_type=event.type,
            delivery_status="accepted",
            correlation_id=event.id,
        )

        return {"status": "accepted", "event_type": event.type}

    if event.type in ("subscription.cancelled", "subscription.canceled"):
        polar_subscription_id = event.data.get("subscription_id")
        if not isinstance(polar_subscription_id, str) or not polar_subscription_id.strip():
            raise HTTPException(
                status_code=400, detail="subscription.cancelled requires subscription_id"
            )

        watcher = watcher_repo.find_by_polar_subscription_id(polar_subscription_id.strip())
        if watcher is not None and watcher.status != "suspended":
            watcher_repo.update_status(watcher.id, "suspended")

        _record_support_webhook_event(
            watcher_id=watcher.id if watcher is not None else None,
            event_type=event.type,
            delivery_status="accepted",
            correlation_id=event.id,
        )

        return {"status": "accepted", "event_type": event.type}

    _record_support_webhook_event(
        watcher_id=None,
        event_type=event.type,
        delivery_status="ignored",
        correlation_id=event.id,
    )
    return {"status": "ignored", "event_type": event.type}


@watchers_router.post("/watchers", response_model=WatcherCreateResponse)
def create_watcher_watch(request: WatcherCreateRequest) -> WatcherCreateResponse:
    """Crée un watcher (ou le réutilise) puis ajoute un dataset surveillé."""

    detail = GetDatasetDetailUseCase(SqlAlchemyDatasetDetailAdapter()).execute(request.dataset_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Dataset {request.dataset_id} not found")

    watcher_repo = SqlAlchemyWatcherRepository()
    watcher = watcher_repo.find_by_email(request.email)
    if watcher is None:
        watcher = watcher_repo.create(email=request.email, token=str(uuid.uuid4()))

    try:
        watcher_repo.add_watched_dataset(
            watcher_id=watcher.id,
            dataset_id=request.dataset_id,
            last_known_metadata_modified=detail.modified,
            last_known_resource_count=len(detail.resources),
            last_known_quality_score=(
                float(detail.quality_score) if detail.quality_score is not None else None
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return WatcherCreateResponse(
        watcher_id=watcher.id,
        email=watcher.email,
        token=watcher.token,
        dataset_id=request.dataset_id,
        status=watcher.status,
    )


@watchers_router.get("/watchers", response_model=WatchersListResponse)
def get_watchers(
    token: str = Query(..., description="Token UUID du watcher")
) -> WatchersListResponse:
    """Retourne les datasets surveillés d'un watcher identifié par token."""

    watcher_repo, watcher = _require_watcher_by_token(token)
    watched_items = [
        item for item in watcher_repo.list_watched_datasets() if item.watcher_id == watcher.id
    ]
    detail_use_case = GetDatasetDetailUseCase(SqlAlchemyDatasetDetailAdapter())
    items = [
        WatchedDatasetItemResponse(
            id=item.id,
            dataset_id=item.dataset_id,
            dataset_title=(
                detail.title
                if (detail := detail_use_case.execute(item.dataset_id)) is not None
                else None
            ),
            created_at=item.created_at,
        )
        for item in watched_items
    ]
    return WatchersListResponse(
        watcher_id=watcher.id,
        email=watcher.email,
        status=watcher.status,
        items=items,
    )


@watchers_router.delete("/watchers/{watched_dataset_id}", status_code=204)
def delete_watcher_watch(
    watched_dataset_id: str,
    token: str = Query(..., description="Token UUID du watcher"),
) -> Response:
    """Supprime une surveillance dataset à partir de son identifiant."""

    watcher_repo, watcher = _require_watcher_by_token(token)
    watched_item = next(
        (
            item
            for item in watcher_repo.list_watched_datasets()
            if item.watcher_id == watcher.id and item.id == watched_dataset_id
        ),
        None,
    )
    if watched_item is None:
        raise HTTPException(status_code=404, detail="Watched dataset not found")

    watcher_repo.remove_watched_dataset(watcher_id=watcher.id, dataset_id=watched_item.dataset_id)
    return Response(status_code=204)


@watchers_router.get("/alerts", response_model=AlertsResponse)
def get_alerts(token: str = Query(..., description="Token UUID du watcher")) -> AlertsResponse:
    """Retourne l'historique des changements des datasets surveillés par le watcher."""

    watcher_repo, watcher = _require_watcher_by_token(token)
    watched_items = [
        item for item in watcher_repo.list_watched_datasets() if item.watcher_id == watcher.id
    ]
    watched_ids = {item.dataset_id for item in watched_items}

    if not watched_ids:
        return AlertsResponse(watcher_id=watcher.id, count=0, items=[])

    with SessionLocal() as session:
        rows = (
            session.query(ChangeLogModel)
            .filter(ChangeLogModel.dataset_id.in_(watched_ids))
            .order_by(ChangeLogModel.detected_at.desc())
            .all()
        )

    detail_use_case = GetDatasetDetailUseCase(SqlAlchemyDatasetDetailAdapter())
    items = [
        AlertItemResponse(
            id=row.id,
            dataset_id=row.dataset_id,
            dataset_title=(
                detail.title
                if (detail := detail_use_case.execute(row.dataset_id)) is not None
                else None
            ),
            change_type=row.change_type,
            previous_value=row.previous_value,
            new_value=row.new_value,
            detected_at=row.detected_at,
            notified_at=row.notified_at,
        )
        for row in rows
    ]
    return AlertsResponse(watcher_id=watcher.id, count=len(items), items=items)


@watchers_router.get("/magic-link/consume", response_model=MagicLinkConsumeResponse)
def consume_magic_link(
    magic: str = Query(..., description="Token magic link brut issu du lien email"),
) -> MagicLinkConsumeResponse:
    """Consomme un magic link temporaire et retourne le token watcher permanent (ADR-030)."""
    token_hash = sha256(magic.encode("utf-8")).hexdigest()
    magic_link_repo = SqlAlchemyMagicLinkRepository()
    magic_link = magic_link_repo.find_by_token_hash(token_hash)
    invalid_magic_link_detail = "Magic link invalide"

    if magic_link is None:
        raise HTTPException(status_code=401, detail=invalid_magic_link_detail)

    now_iso = datetime.now(UTC).isoformat()

    if magic_link.expires_at < now_iso:
        raise HTTPException(status_code=401, detail=invalid_magic_link_detail)

    if magic_link.used_at is not None:
        raise HTTPException(status_code=401, detail=invalid_magic_link_detail)

    watcher_repo = SqlAlchemyWatcherRepository()
    watcher = watcher_repo.find_by_id(magic_link.watcher_id)

    if watcher is None or watcher.status != "active":
        raise HTTPException(status_code=401, detail=invalid_magic_link_detail)

    magic_link_repo.mark_used(magic_link.id, now_iso)

    return MagicLinkConsumeResponse(
        token=watcher.token,
        watcher_id=watcher.id,
        email=watcher.email,
        status=watcher.status,
    )


@watchers_router.post("/magic-link", status_code=200)
def request_magic_link(body: MagicLinkRequestBody) -> dict[str, str]:
    """Génère et envoie un magic link par email à un watcher actif (ADR-030)."""
    _status_sent: dict[str, str] = {"status": "sent"}

    watcher_repo = SqlAlchemyWatcherRepository()
    normalized_email = body.email.strip()
    watcher = watcher_repo.find_by_email(normalized_email) or watcher_repo.find_by_email(
        normalized_email.lower()
    )

    if watcher is None or watcher.status != "active":
        return _status_sent

    from app.core.config import get_settings

    token, _issued_at = _issue_magic_link_for_watcher(watcher.id)
    settings = get_settings()
    _dispatch_magic_link_email(
        watcher=watcher,
        subject="[PDS-Portail] Votre lien d'accès aux alertes",
        template_name="magic_link_email",
        email_kind="magic_link",
        template_context={"alerts_link": f"https://pds-portail.ch/alertes?magic={token}"},
        smtp_host=settings.smtp_host,
        smtp_port=settings.smtp_port,
        smtp_user=settings.smtp_user,
        smtp_password=settings.smtp_password,
        smtp_from=settings.smtp_from,
    )

    return _status_sent

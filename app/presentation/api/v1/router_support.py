import hmac
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from app.core.config import get_settings
from app.infrastructure.persistence.database import SessionLocal
from app.infrastructure.persistence.models import (
    MagicLinkModel,
    SupportEmailEventModel,
    SupportWebhookEventModel,
    WatchedDatasetModel,
)
from app.infrastructure.persistence.watcher_repository import SqlAlchemyWatcherRepository
from app.presentation.api.v1.schemas import (
    InternalSupportEmailDeliverabilityResponse,
    InternalSupportMagicLinkResendRequest,
    InternalSupportMagicLinkResendResponse,
    InternalSupportMagicLinkStateResponse,
    InternalSupportSubscriptionResponse,
    InternalSupportWatcherLookupResponse,
    InternalSupportWebhookEventResponse,
    InternalSupportWebhookEventsResponse,
)
from app.presentation.api.v1.watcher_support import (
    audit_internal_support_event as _audit_internal_support_event,
)
from app.presentation.api.v1.watcher_support import (
    dispatch_magic_link_email as _dispatch_magic_link_email,
)
from app.presentation.api.v1.watcher_support import (
    issue_magic_link_for_watcher as _issue_magic_link_for_watcher,
)
from app.presentation.api.v1.watcher_support import (
    mask_identifier as _mask_identifier,
)
from app.presentation.api.v1.watcher_support import (
    support_now_iso as _support_now_iso,
)

support_router = APIRouter()


def _require_internal_support_access(
    authorization: str | None = Header(None, alias="Authorization"),
    x_operator_id: str | None = Header(None, alias="X-Operator-Id"),
    x_request_id: str | None = Header(None, alias="X-Request-Id"),
) -> tuple[str, str | None]:
    settings = get_settings()
    expected_token = settings.internal_api_token
    if not expected_token:
        raise HTTPException(status_code=503, detail="INTERNAL_API_TOKEN not configured")
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Invalid bearer token")

    if not hmac.compare_digest(token.strip(), expected_token):
        raise HTTPException(status_code=401, detail="Invalid bearer token")

    operator_id = x_operator_id.strip() if x_operator_id and x_operator_id.strip() else "support"
    request_id = x_request_id.strip() if x_request_id and x_request_id.strip() else None
    return operator_id, request_id


@support_router.get(
    "/internal/support/watchers/by-email",
    response_model=InternalSupportWatcherLookupResponse,
)
def internal_support_get_watcher_by_email(
    email: str = Query(..., description="Adresse email de l'abonne"),
    support_context: tuple[str, str | None] = Depends(_require_internal_support_access),
) -> InternalSupportWatcherLookupResponse:
    operator_id, request_id = support_context
    normalized_email = email.strip()
    if "@" not in normalized_email:
        _audit_internal_support_event(
            route="/api/v1/internal/support/watchers/by-email",
            method="GET",
            outcome="invalid_input",
            operator_id=operator_id,
            email=normalized_email,
            request_id=request_id,
        )
        raise HTTPException(status_code=400, detail="Invalid email")

    watcher_repo = SqlAlchemyWatcherRepository()
    watcher = watcher_repo.find_by_email(normalized_email) or watcher_repo.find_by_email(
        normalized_email.lower()
    )
    if watcher is None:
        _audit_internal_support_event(
            route="/api/v1/internal/support/watchers/by-email",
            method="GET",
            outcome="not_found",
            operator_id=operator_id,
            email=normalized_email,
            request_id=request_id,
        )
        raise HTTPException(status_code=404, detail="Watcher not found")

    with SessionLocal() as session:
        watched_datasets_count = (
            session.query(WatchedDatasetModel)
            .filter(WatchedDatasetModel.watcher_id == watcher.id)
            .count()
        )
        last_webhook_row = (
            session.query(SupportWebhookEventModel)
            .filter(SupportWebhookEventModel.watcher_id == watcher.id)
            .order_by(SupportWebhookEventModel.received_at.desc())
            .first()
        )
        last_magic_link_row = (
            session.query(MagicLinkModel)
            .filter(MagicLinkModel.watcher_id == watcher.id)
            .order_by(MagicLinkModel.created_at.desc())
            .first()
        )

    _audit_internal_support_event(
        route="/api/v1/internal/support/watchers/by-email",
        method="GET",
        outcome="ok",
        operator_id=operator_id,
        watcher_id=watcher.id,
        email=normalized_email,
        request_id=request_id,
    )

    return InternalSupportWatcherLookupResponse(
        watcher_id=watcher.id,
        watcher_status=watcher.status,
        subscription_id_present=watcher.polar_subscription_id is not None,
        watched_datasets_count=watched_datasets_count,
        last_webhook_at=last_webhook_row.received_at if last_webhook_row else None,
        last_magic_link_at=last_magic_link_row.created_at if last_magic_link_row else None,
    )


@support_router.get(
    "/internal/support/watchers/{watcher_id}/subscription",
    response_model=InternalSupportSubscriptionResponse,
)
def internal_support_get_subscription(
    watcher_id: str,
    support_context: tuple[str, str | None] = Depends(_require_internal_support_access),
) -> InternalSupportSubscriptionResponse:
    operator_id, request_id = support_context
    watcher_repo = SqlAlchemyWatcherRepository()
    watcher = watcher_repo.find_by_id(watcher_id)
    if watcher is None:
        _audit_internal_support_event(
            route=f"/api/v1/internal/support/watchers/{watcher_id}/subscription",
            method="GET",
            outcome="not_found",
            operator_id=operator_id,
            watcher_id=watcher_id,
            request_id=request_id,
        )
        raise HTTPException(status_code=404, detail="Watcher not found")

    _audit_internal_support_event(
        route=f"/api/v1/internal/support/watchers/{watcher_id}/subscription",
        method="GET",
        outcome="ok",
        operator_id=operator_id,
        watcher_id=watcher.id,
        request_id=request_id,
    )

    return InternalSupportSubscriptionResponse(
        watcher_id=watcher.id,
        subscription_state=watcher.status if watcher.polar_subscription_id else "missing",
        subscription_id_masked=_mask_identifier(watcher.polar_subscription_id),
        updated_at=watcher.updated_at,
    )


@support_router.get(
    "/internal/support/watchers/{watcher_id}/webhooks/latest",
    response_model=InternalSupportWebhookEventsResponse,
)
def internal_support_get_latest_webhooks(
    watcher_id: str,
    limit: int = Query(20, ge=1, le=50),
    support_context: tuple[str, str | None] = Depends(_require_internal_support_access),
) -> InternalSupportWebhookEventsResponse:
    operator_id, request_id = support_context
    watcher_repo = SqlAlchemyWatcherRepository()
    watcher = watcher_repo.find_by_id(watcher_id)
    if watcher is None:
        _audit_internal_support_event(
            route=f"/api/v1/internal/support/watchers/{watcher_id}/webhooks/latest",
            method="GET",
            outcome="not_found",
            operator_id=operator_id,
            watcher_id=watcher_id,
            request_id=request_id,
        )
        raise HTTPException(status_code=404, detail="Watcher not found")

    with SessionLocal() as session:
        rows = (
            session.query(SupportWebhookEventModel)
            .filter(SupportWebhookEventModel.watcher_id == watcher.id)
            .order_by(SupportWebhookEventModel.received_at.desc())
            .limit(limit)
            .all()
        )

    _audit_internal_support_event(
        route=f"/api/v1/internal/support/watchers/{watcher_id}/webhooks/latest",
        method="GET",
        outcome="ok",
        operator_id=operator_id,
        watcher_id=watcher.id,
        request_id=request_id,
    )

    return InternalSupportWebhookEventsResponse(
        watcher_id=watcher.id,
        items=[
            InternalSupportWebhookEventResponse(
                event_type=row.event_type,
                received_at=row.received_at,
                delivery_status=row.delivery_status,
                correlation_id=row.correlation_id,
            )
            for row in rows
        ],
    )


@support_router.get(
    "/internal/support/watchers/{watcher_id}/magic-links/state",
    response_model=InternalSupportMagicLinkStateResponse,
)
def internal_support_get_magic_link_state(
    watcher_id: str,
    support_context: tuple[str, str | None] = Depends(_require_internal_support_access),
) -> InternalSupportMagicLinkStateResponse:
    operator_id, request_id = support_context
    watcher_repo = SqlAlchemyWatcherRepository()
    watcher = watcher_repo.find_by_id(watcher_id)
    if watcher is None:
        _audit_internal_support_event(
            route=f"/api/v1/internal/support/watchers/{watcher_id}/magic-links/state",
            method="GET",
            outcome="not_found",
            operator_id=operator_id,
            watcher_id=watcher_id,
            request_id=request_id,
        )
        raise HTTPException(status_code=404, detail="Watcher not found")

    now_iso = _support_now_iso()
    with SessionLocal() as session:
        magic_rows = (
            session.query(MagicLinkModel)
            .filter(MagicLinkModel.watcher_id == watcher.id)
            .order_by(MagicLinkModel.created_at.desc())
            .all()
        )

    active_unexpired_count = sum(
        1 for row in magic_rows if row.used_at is None and row.expires_at > now_iso
    )
    expired_unconsumed_count = sum(
        1 for row in magic_rows if row.used_at is None and row.expires_at <= now_iso
    )
    last_issued_at = magic_rows[0].created_at if magic_rows else None
    last_used_candidates = [row.used_at for row in magic_rows if row.used_at is not None]

    _audit_internal_support_event(
        route=f"/api/v1/internal/support/watchers/{watcher_id}/magic-links/state",
        method="GET",
        outcome="ok",
        operator_id=operator_id,
        watcher_id=watcher.id,
        request_id=request_id,
    )

    return InternalSupportMagicLinkStateResponse(
        watcher_id=watcher.id,
        last_issued_at=last_issued_at,
        last_used_at=max(last_used_candidates) if last_used_candidates else None,
        active_unexpired_count=active_unexpired_count,
        expired_unconsumed_count=expired_unconsumed_count,
    )


@support_router.get(
    "/internal/support/watchers/{watcher_id}/email-deliverability",
    response_model=InternalSupportEmailDeliverabilityResponse,
)
def internal_support_get_email_deliverability(
    watcher_id: str,
    support_context: tuple[str, str | None] = Depends(_require_internal_support_access),
) -> InternalSupportEmailDeliverabilityResponse:
    operator_id, request_id = support_context
    watcher_repo = SqlAlchemyWatcherRepository()
    watcher = watcher_repo.find_by_id(watcher_id)
    if watcher is None:
        _audit_internal_support_event(
            route=f"/api/v1/internal/support/watchers/{watcher_id}/email-deliverability",
            method="GET",
            outcome="not_found",
            operator_id=operator_id,
            watcher_id=watcher_id,
            request_id=request_id,
        )
        raise HTTPException(status_code=404, detail="Watcher not found")

    threshold_24h = (datetime.now(UTC) - timedelta(hours=24)).isoformat()
    with SessionLocal() as session:
        rows = (
            session.query(SupportEmailEventModel)
            .filter(SupportEmailEventModel.watcher_id == watcher.id)
            .order_by(SupportEmailEventModel.created_at.desc())
            .all()
        )

    last_row = rows[0] if rows else None
    recent_error_rows = [
        row for row in rows if row.status == "failed" and row.created_at >= threshold_24h
    ]

    _audit_internal_support_event(
        route=f"/api/v1/internal/support/watchers/{watcher_id}/email-deliverability",
        method="GET",
        outcome="ok",
        operator_id=operator_id,
        watcher_id=watcher.id,
        request_id=request_id,
    )

    return InternalSupportEmailDeliverabilityResponse(
        watcher_id=watcher.id,
        last_send_status=last_row.status if last_row else None,
        last_send_at=last_row.created_at if last_row else None,
        provider_message_id_masked=last_row.provider_message_id_masked if last_row else None,
        recent_error_code=recent_error_rows[0].error_code if recent_error_rows else None,
        recent_error_count_24h=len(recent_error_rows),
    )


@support_router.post(
    "/internal/support/watchers/{watcher_id}/magic-link/resend",
    response_model=InternalSupportMagicLinkResendResponse,
)
def internal_support_resend_magic_link(
    watcher_id: str,
    body: InternalSupportMagicLinkResendRequest,
    support_context: tuple[str, str | None] = Depends(_require_internal_support_access),
) -> InternalSupportMagicLinkResendResponse:
    operator_id, request_id = support_context
    if not body.reason.strip():
        _audit_internal_support_event(
            route=f"/api/v1/internal/support/watchers/{watcher_id}/magic-link/resend",
            method="POST",
            outcome="invalid_input",
            operator_id=operator_id,
            watcher_id=watcher_id,
            request_id=request_id,
        )
        raise HTTPException(status_code=400, detail="Reason is required")

    watcher_repo = SqlAlchemyWatcherRepository()
    watcher = watcher_repo.find_by_id(watcher_id)
    if watcher is None:
        _audit_internal_support_event(
            route=f"/api/v1/internal/support/watchers/{watcher_id}/magic-link/resend",
            method="POST",
            outcome="not_found",
            operator_id=operator_id,
            watcher_id=watcher_id,
            request_id=request_id,
            reason=body.reason,
        )
        raise HTTPException(status_code=404, detail="Watcher not found")

    if watcher.status != "active":
        _audit_internal_support_event(
            route=f"/api/v1/internal/support/watchers/{watcher_id}/magic-link/resend",
            method="POST",
            outcome="conflict",
            operator_id=operator_id,
            watcher_id=watcher.id,
            request_id=request_id,
            reason=body.reason,
        )
        raise HTTPException(status_code=409, detail="Watcher suspended")

    threshold_60s = (datetime.now(UTC) - timedelta(seconds=60)).isoformat()
    with SessionLocal() as session:
        latest_support_magic_link = (
            session.query(SupportEmailEventModel)
            .filter(
                SupportEmailEventModel.watcher_id == watcher.id,
                SupportEmailEventModel.email_kind == "magic_link",
            )
            .order_by(SupportEmailEventModel.created_at.desc())
            .first()
        )

    if (
        latest_support_magic_link is not None
        and latest_support_magic_link.created_at >= threshold_60s
    ):
        _audit_internal_support_event(
            route=f"/api/v1/internal/support/watchers/{watcher_id}/magic-link/resend",
            method="POST",
            outcome="rate_limited",
            operator_id=operator_id,
            watcher_id=watcher.id,
            request_id=request_id,
            reason=body.reason,
        )
        raise HTTPException(status_code=429, detail="Magic link resend rate limited")

    token, issued_at = _issue_magic_link_for_watcher(watcher.id)
    settings = get_settings()
    dispatch_status = _dispatch_magic_link_email(
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

    if dispatch_status == "failed":
        _audit_internal_support_event(
            route=f"/api/v1/internal/support/watchers/{watcher_id}/magic-link/resend",
            method="POST",
            outcome="error",
            operator_id=operator_id,
            watcher_id=watcher.id,
            request_id=request_id,
            reason=body.reason,
        )
        raise HTTPException(status_code=500, detail="Internal error")

    audit_id = _audit_internal_support_event(
        route=f"/api/v1/internal/support/watchers/{watcher_id}/magic-link/resend",
        method="POST",
        outcome=dispatch_status,
        operator_id=operator_id,
        watcher_id=watcher.id,
        email=watcher.email,
        request_id=request_id,
        reason=body.reason,
    )

    return InternalSupportMagicLinkResendResponse(
        audit_id=audit_id,
        dispatch_status=dispatch_status,
        issued_at=issued_at,
    )

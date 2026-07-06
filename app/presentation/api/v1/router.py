import hmac
import logging
import uuid
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any, Literal, cast

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from pydantic import BaseModel

from app.application.ports.license_repository import License
from app.application.ports.watcher_repository import Watcher
from app.application.use_cases.cached_get_dataset_detail import CachedGetDatasetDetailUseCase
from app.application.use_cases.cached_search_datasets import CachedSearchDatasetsUseCase
from app.application.use_cases.compare_datasets import (
    CompareDatasetsUseCase,
    InvalidCompareRequestError,
)
from app.application.use_cases.detect_changes import DetectChangesUseCase
from app.application.use_cases.explore_resource import explore_resource as explore_resource_use_case
from app.application.use_cases.get_dataset_detail import GetDatasetDetailUseCase
from app.application.use_cases.get_health_status import GetHealthStatusUseCase
from app.application.use_cases.get_resource_detail import GetResourceDetailUseCase
from app.application.use_cases.invalidate_cache_after_sync import invalidate_cache_after_sync
from app.application.use_cases.run_sync_cycle import RunSyncCycleUseCase
from app.application.use_cases.search_datasets import SearchDatasetsUseCase
from app.application.use_cases.send_alerts import SendAlertsUseCase
from app.core.config import get_settings
from app.infrastructure.external.ckan.client import CkanHttpClient
from app.infrastructure.persistence.cache_read_repository import SqlAlchemyCacheReadRepository
from app.infrastructure.persistence.cache_repository import SqlAlchemyCacheRepository
from app.infrastructure.persistence.changelog_repository import SqlAlchemyChangeLogRepository
from app.infrastructure.persistence.compare_adapter import SqlAlchemyCompareAdapter
from app.infrastructure.persistence.database import SessionLocal
from app.infrastructure.persistence.dataset_detail_adapter import SqlAlchemyDatasetDetailAdapter
from app.infrastructure.persistence.license_repository import SqlAlchemyLicenseRepository
from app.infrastructure.persistence.magic_link_repository import SqlAlchemyMagicLinkRepository
from app.infrastructure.persistence.models import (
    ChangeLogModel,
    MagicLinkModel,
    SupportAuditModel,
    SupportEmailEventModel,
    SupportWebhookEventModel,
    WatchedDatasetModel,
)
from app.infrastructure.persistence.query_cache_repository import SqlAlchemyQueryCacheRepository
from app.infrastructure.persistence.search_adapter import SqlAlchemySearchAdapter
from app.infrastructure.persistence.watcher_repository import SqlAlchemyWatcherRepository
from app.presentation.api.dependencies import require_license_without_quota_check
from app.presentation.api.v1.schemas import (
    CompareRequest,
    CompareResponse,
    DatasetDetailResponse,
    ExploreResourceResponse,
    ResourceDetailResponse,
    SearchResponse,
    TopQueriesResponse,
    ZeroResultsResponse,
)
from app.presentation.api.v1.webhooks import (
    PolarWebhookEvent,
    WebhookVerificationError,
    verify_polar_webhook,
)

logger = logging.getLogger(__name__)

api_router = APIRouter(prefix="/api/v1")


class HealthResponse(BaseModel):
    """Reponse minimale de sante service/cache."""

    status: str
    last_sync: str | None


class CacheCountsResponse(BaseModel):
    """Compteurs minimaux du cache."""

    organizations: int
    datasets: int
    resources: int


class InternalCacheResponse(BaseModel):
    """Vue interne pour verifier qu'un cache peuple est consultable."""

    status: str
    last_sync: str | None
    cache_populated: bool
    counts: CacheCountsResponse


class WatcherCreateRequest(BaseModel):
    """Requete de creation d'une surveillance dataset."""

    email: str
    dataset_id: str


class WatcherCreateResponse(BaseModel):
    """Reponse de creation de watcher/surveillance."""

    watcher_id: str
    email: str
    token: str
    dataset_id: str
    status: str


class WatchedDatasetItemResponse(BaseModel):
    """Element de dataset surveille expose a l'utilisateur."""

    id: str
    dataset_id: str
    dataset_title: str | None
    created_at: str


class WatchersListResponse(BaseModel):
    """Liste des datasets surveilles pour un token watcher."""

    watcher_id: str
    email: str
    status: str
    items: list[WatchedDatasetItemResponse]


class AlertItemResponse(BaseModel):
    """Entree d'alerte pour un changement detecte."""

    id: str
    dataset_id: str
    dataset_title: str | None
    change_type: str
    previous_value: str | None
    new_value: str | None
    detected_at: str
    notified_at: str | None


class AlertsResponse(BaseModel):
    """Reponse de consultation des alertes d'un watcher."""

    watcher_id: str
    count: int
    items: list[AlertItemResponse]


class MagicLinkConsumeResponse(BaseModel):
    """Réponse après consommation réussie d'un magic link (ADR-030)."""

    token: str
    watcher_id: str
    email: str
    status: str


class MagicLinkRequestBody(BaseModel):
    """Corps de la requête pour demander un nouveau magic link par email."""

    email: str


class InternalSupportWatcherLookupResponse(BaseModel):
    """Vue redigée pour retrouver un watcher par email côté support."""

    watcher_id: str
    watcher_status: str
    subscription_id_present: bool
    watched_datasets_count: int
    last_webhook_at: str | None
    last_magic_link_at: str | None


class InternalSupportSubscriptionResponse(BaseModel):
    """Etat redigé d'un abonnement watcher pour le support interne."""

    watcher_id: str
    subscription_state: str
    subscription_id_masked: str | None
    updated_at: str


class InternalSupportWebhookEventResponse(BaseModel):
    """Evenement webhook redigé expose par le support interne."""

    event_type: str
    received_at: str
    delivery_status: str
    correlation_id: str | None


class InternalSupportWebhookEventsResponse(BaseModel):
    """Historique recent des webhooks Polar associes a un watcher."""

    watcher_id: str
    items: list[InternalSupportWebhookEventResponse]


class InternalSupportMagicLinkStateResponse(BaseModel):
    """Etat des magic links temporaires pour le support interne."""

    watcher_id: str
    last_issued_at: str | None
    last_used_at: str | None
    active_unexpired_count: int
    expired_unconsumed_count: int


class InternalSupportEmailDeliverabilityResponse(BaseModel):
    """Indicateurs rediges sur l'envoi email pour un watcher."""

    watcher_id: str
    last_send_status: str | None
    last_send_at: str | None
    provider_message_id_masked: str | None
    recent_error_code: str | None
    recent_error_count_24h: int


class InternalSupportMagicLinkResendRequest(BaseModel):
    """Corps de la requête de renvoi de magic link support."""

    reason: str


class InternalSupportMagicLinkResendResponse(BaseModel):
    """Réponse auditee d'un renvoi de magic link support."""

    audit_id: str
    dispatch_status: str
    issued_at: str


def _support_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _redact_email(email: str) -> str:
    normalized = email.strip().lower().encode("utf-8")
    return sha256(normalized).hexdigest()[:12]


def _mask_identifier(value: str | None) -> str | None:
    if value is None:
        return None
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}…{value[-4:]}"


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


def _audit_internal_support_event(
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
                timestamp=_support_now_iso(),
                route=route,
                method=method,
                outcome=outcome,
                operator_id=operator_id,
                watcher_id=watcher_id,
                email_hash_prefix=_redact_email(email) if email else None,
                request_id=request_id,
                reason=reason,
            )
        )
        session.commit()
    return audit_id


def _record_support_webhook_event(
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
                received_at=_support_now_iso(),
                delivery_status=delivery_status,
                correlation_id=correlation_id,
            )
        )
        session.commit()


def _record_support_email_event(
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
                created_at=_support_now_iso(),
                provider_message_id_masked=provider_message_id_masked,
                error_code=error_code,
            )
        )
        session.commit()


def _issue_magic_link_for_watcher(watcher_id: str) -> tuple[str, str]:
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


def _dispatch_magic_link_email(
    *,
    watcher: Watcher,
    subject: str,
    template_name: str,
    email_kind: str,
    template_context: dict[str, str],
) -> str:
    import smtplib
    import ssl
    from email.message import EmailMessage
    from pathlib import Path

    settings = get_settings()
    email_hash_prefix = _redact_email(watcher.email)

    if (
        not settings.smtp_host
        or not settings.smtp_user
        or not settings.smtp_password
        or not settings.smtp_from
    ):
        logger.warning(
            "SMTP incomplet pour support email watcher=%s email_hash=%s",
            watcher.id,
            email_hash_prefix,
        )
        _record_support_email_event(
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
        _record_support_email_event(
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
        message["From"] = settings.smtp_from
        message["To"] = watcher.email
        message.set_content(text_body)
        message.add_alternative(html_body, subtype="html")

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(message)

        _record_support_email_event(
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
        _record_support_email_event(
            watcher_id=watcher.id,
            email_kind=email_kind,
            status="failed",
            error_code=type(exc).__name__,
        )
        return "failed"


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


def _send_welcome_email_for_watcher(
    watcher: Watcher,
    dataset: DatasetDetailResponse,
) -> None:
    """Envoie un email de bienvenue avec magic link après inscription Polar (PDS-90).

    Utile uniquement après order.created. Les erreurs sont loggées mais ne bloquent
    pas la réponse HTTP 200 au webhook Polar (idempotence).
    """
    import hashlib
    import logging
    import smtplib
    import ssl
    from datetime import UTC, datetime, timedelta
    from email.message import EmailMessage
    from pathlib import Path

    logger = logging.getLogger(__name__)
    settings = get_settings()
    email_hash_prefix = _redact_email(watcher.email)

    # Vérifications minimales
    if (
        not settings.smtp_host
        or not settings.smtp_user
        or not settings.smtp_password
        or not settings.smtp_from
    ):
        logger.warning(
            "Impossible d'envoyer email bienvenue pour watcher=%s email_hash=%s: "
            "config SMTP incomplète",
            watcher.id,
            email_hash_prefix,
        )
        _record_support_email_event(
            watcher_id=watcher.id,
            email_kind="welcome",
            status="queued",
            error_code="smtp_missing",
        )
        return

    try:
        # Génère un magic link temporaire (15 minutes)
        token = str(uuid.uuid4())
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=15)

        magic_link_repo = SqlAlchemyMagicLinkRepository()
        magic_link_repo.create(
            watcher_id=watcher.id,
            token_hash=token_hash,
            created_at=now.isoformat(),
            expires_at=expires_at.isoformat(),
        )

        # Construit les URLs
        alerts_link = f"https://pds-portail.ch/alertes?magic={token}"
        dataset_link = f"https://pds-portail.ch/dataset/{dataset.id}"

        # Charge les templates
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
            _record_support_email_event(
                watcher_id=watcher.id,
                email_kind="welcome",
                status="queued",
                error_code="template_missing",
            )
            return

        html_content = html_template_path.read_text(encoding="utf-8")
        text_content = text_template_path.read_text(encoding="utf-8")

        # Render templates using str.format (cohérent avec SendAlertsUseCase)
        context = {
            "dataset_title": dataset.title,
            "alerts_link": alerts_link,
            "dataset_link": dataset_link,
        }

        html_body = html_content.format(**context)
        text_body = text_content.format(**context)

        # Construit le message email
        message = EmailMessage()
        message["Subject"] = f"[PDS-Portail] Bienvenue ! Surveillance activée pour {dataset.title}"
        message["From"] = settings.smtp_from
        message["To"] = watcher.email
        message.set_content(text_body)
        message.add_alternative(html_body, subtype="html")

        # Envoie l'email
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(message)

        logger.info(
            "Email bienvenue envoyé pour watcher=%s email_hash=%s dataset=%s",
            watcher.id,
            email_hash_prefix,
            dataset.id,
        )
        _record_support_email_event(
            watcher_id=watcher.id,
            email_kind="welcome",
            status="sent",
        )
    except Exception as exc:
        # Les erreurs d'email ne doivent pas bloquer la réponse HTTP
        logger.error(
            "Erreur lors de l'envoi de l'email bienvenue watcher=%s email_hash=%s: %s",
            watcher.id,
            email_hash_prefix,
            exc,
            exc_info=True,
        )
        _record_support_email_event(
            watcher_id=watcher.id,
            email_kind="welcome",
            status="failed",
            error_code=type(exc).__name__,
        )


@api_router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Expose l'etat du service et le dernier horodatage de synchronisation."""

    snapshot = GetHealthStatusUseCase(SqlAlchemyCacheReadRepository()).execute()
    return HealthResponse(status=snapshot.status, last_sync=snapshot.last_sync)


@api_router.get("/internal/cache", response_model=InternalCacheResponse)
def internal_cache_status() -> InternalCacheResponse:
    """Lecture interne minimale pour verifier que le cache est consultable."""

    snapshot = GetHealthStatusUseCase(SqlAlchemyCacheReadRepository()).execute()
    return InternalCacheResponse(
        status=snapshot.status,
        last_sync=snapshot.last_sync,
        cache_populated=snapshot.cache_populated,
        counts=CacheCountsResponse(
            organizations=snapshot.counts.organizations,
            datasets=snapshot.counts.datasets,
            resources=snapshot.counts.resources,
        ),
    )


@api_router.get("/search", response_model=SearchResponse)
def search(
    q: str | None = Query(None, description="Texte libre: titre, description"),
    offset: int = Query(0, ge=0, description="Position de pagination"),
    limit: int = Query(20, ge=1, le=100, description="Resultats par page"),
    org: str | None = Query(None, description="Filtrer par ID organisation"),
    fmt: str | None = Query(None, description="Filtrer par format ressource"),
    tag: str | None = Query(None, description="Filtrer par tag (exact match)"),
    sort: Literal[
        "modified_desc",
        "modified_asc",
        "quality_desc",
        "quality_asc",
        "hybrid",
        "title_asc",
        "title_desc",
    ] = Query("modified_desc", description="Strategie de tri explicite"),
) -> SearchResponse:
    """Recherche les datasets avec pagination et filtres.

    Supporte la recherche full-text sur titre/description ainsi que
    le filtrage par organisation, format de ressource, et tag. Inclut les facettes
    pour construire une interface de recherche facettee.

    Query params:
        q: Texte libre (optionnel)
        offset: Premiere position (defaut 0)
        limit: Resultats par page (1-100, defaut 20)
        org: Filtrer par ID organisation (optionnel)
        fmt: Filtrer par format (CSV, JSON, etc) (optionnel)
        tag: Filtrer par tag specifique (optionnel)
        sort: Strategie de tri explicite

    Returns:
        SearchResponse avec datasets pagines et facettes d'agregation
    """

    settings = get_settings()
    if settings.query_cache_enabled:
        return CachedSearchDatasetsUseCase(
            repository=SqlAlchemySearchAdapter(),
            cache=SqlAlchemyQueryCacheRepository(),
            ttl_seconds=settings.query_cache_ttl_seconds,
        ).execute(
            query=q,
            offset=offset,
            limit=limit,
            org_filter=org,
            format_filter=fmt,
            tag_filter=tag,
            sort=sort,
        )
    return SearchDatasetsUseCase(SqlAlchemySearchAdapter()).execute(
        query=q,
        offset=offset,
        limit=limit,
        org_filter=org,
        format_filter=fmt,
        tag_filter=tag,
        sort=sort,
    )


@api_router.get("/dataset/{dataset_id}", response_model=DatasetDetailResponse)
def get_dataset(dataset_id: str) -> DatasetDetailResponse:
    """Retourne le detail complet d'un dataset avec ses ressources.

    Inclut les indicateurs de qualite (quality_score, completeness, freshness_days),
    la structure du dataset et les modes d'acces disponibles.

    Path params:
        dataset_id: UUID du dataset CKAN

    Returns:
        DatasetDetailResponse avec detail complet ou 404 si non trouve
    """

    settings = get_settings()
    if settings.query_cache_enabled:
        detail = CachedGetDatasetDetailUseCase(
            repository=SqlAlchemyDatasetDetailAdapter(),
            cache=SqlAlchemyQueryCacheRepository(),
            ttl_seconds=settings.query_cache_ttl_seconds,
        ).execute(dataset_id)
    else:
        detail = GetDatasetDetailUseCase(SqlAlchemyDatasetDetailAdapter()).execute(dataset_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")
    return detail


@api_router.get("/resource/{resource_id}", response_model=ResourceDetailResponse)
def get_resource(resource_id: str) -> ResourceDetailResponse:
    """Retourne le detail d'une ressource avec reference au dataset.

    Path params:
        resource_id: UUID de la ressource CKAN

    Returns:
        ResourceDetailResponse ou 404 si non trouve
    """

    detail = GetResourceDetailUseCase(SqlAlchemyDatasetDetailAdapter()).execute(resource_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Resource {resource_id} not found")
    return detail


@api_router.post("/webhooks/polar")
async def webhook_polar(
    request: Request,
    x_polar_signature: str | None = Header(None, alias="X-Polar-Signature"),
) -> dict[str, str]:
    """Endpoint public Polar : vérifie signature puis traite l'événement métier."""

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

        # Envoie l'email de bienvenue avec magic link (PDS-90 SPEC-009)
        # Les erreurs d'email ne bloquent pas la réponse (idempotence webhook)
        try:
            _send_welcome_email_for_watcher(watcher, detail)
        except Exception as exc:
            logger.warning("Erreur email bienvenue (webhook continue): %s", exc)

        _record_support_webhook_event(
            watcher_id=watcher.id,
            event_type=event.type,
            delivery_status="accepted",
            correlation_id=event.id,
        )

        return {"status": "accepted", "event_type": event.type}

    if event.type == "subscription.cancelled":
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


@api_router.post("/watchers", response_model=WatcherCreateResponse)
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


@api_router.get("/watchers", response_model=WatchersListResponse)
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


@api_router.delete("/watchers/{watched_dataset_id}", status_code=204)
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


@api_router.get("/alerts", response_model=AlertsResponse)
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


@api_router.get("/magic-link/consume", response_model=MagicLinkConsumeResponse)
def consume_magic_link(
    magic: str = Query(..., description="Token magic link brut issu du lien email"),
) -> MagicLinkConsumeResponse:
    """Consomme un magic link temporaire et retourne le token watcher permanent (ADR-030).

    Vérifie le hash SHA-256, l'expiration (15 min), l'usage unique et le statut watcher.
    Marque used_at à la première et unique utilisation.
    """
    import hashlib
    from datetime import UTC, datetime

    token_hash = hashlib.sha256(magic.encode("utf-8")).hexdigest()
    magic_link_repo = SqlAlchemyMagicLinkRepository()
    magic_link = magic_link_repo.find_by_token_hash(token_hash)

    if magic_link is None:
        raise HTTPException(status_code=401, detail="Magic link invalide")

    now_iso = datetime.now(UTC).isoformat()

    if magic_link.expires_at < now_iso:
        raise HTTPException(status_code=401, detail="Magic link expiré")

    if magic_link.used_at is not None:
        raise HTTPException(status_code=401, detail="Magic link déjà utilisé")

    watcher_repo = SqlAlchemyWatcherRepository()
    watcher = watcher_repo.find_by_id(magic_link.watcher_id)

    if watcher is None or watcher.status != "active":
        raise HTTPException(status_code=401, detail="Accès refusé")

    # Marque le magic link comme consommé (usage unique ADR-030)
    magic_link_repo.mark_used(magic_link.id, now_iso)

    return MagicLinkConsumeResponse(
        token=watcher.token,
        watcher_id=watcher.id,
        email=watcher.email,
        status=watcher.status,
    )


@api_router.get(
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


@api_router.get(
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


@api_router.get(
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


@api_router.get(
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


@api_router.get(
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


@api_router.post(
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
    dispatch_status = _dispatch_magic_link_email(
        watcher=watcher,
        subject="[PDS-Portail] Votre lien d'accès aux alertes",
        template_name="magic_link_email",
        email_kind="magic_link",
        template_context={"alerts_link": f"https://pds-portail.ch/alertes?magic={token}"},
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


@api_router.post("/magic-link", status_code=200)
def request_magic_link(body: MagicLinkRequestBody) -> dict[str, str]:
    """Génère et envoie un magic link par email à un watcher actif (ADR-030).

    Retourne toujours {"status": "sent"} pour éviter l'énumération d'emails.
    Si le watcher n'existe pas ou est inactif, la réponse est identique.
    """
    # Anti-énumération : on répond toujours de la même façon
    _status_sent: dict[str, str] = {"status": "sent"}

    watcher_repo = SqlAlchemyWatcherRepository()
    normalized_email = body.email.strip()
    watcher = watcher_repo.find_by_email(normalized_email) or watcher_repo.find_by_email(
        normalized_email.lower()
    )

    if watcher is None or watcher.status != "active":
        return _status_sent

    token, _issued_at = _issue_magic_link_for_watcher(watcher.id)
    _dispatch_magic_link_email(
        watcher=watcher,
        subject="[PDS-Portail] Votre lien d'accès aux alertes",
        template_name="magic_link_email",
        email_kind="magic_link",
        template_context={"alerts_link": f"https://pds-portail.ch/alertes?magic={token}"},
    )

    return _status_sent


@api_router.post("/compare", response_model=CompareResponse)
def compare_datasets(request: CompareRequest) -> CompareResponse:
    """Compare 2 a 4 datasets sur des criteres homogenes (PDS-43).

    Charge les datasets en une seule requete batch et retourne les champs
    comparables : qualite, fraicheur, formats, ressources, tags, etc.

    Body:
        ids: Liste de 2 a 4 IDs de datasets

    Returns:
        CompareResponse avec les items trouves (ordre preserve)

    Raises:
        400: Moins de 2 IDs fournis ou IDs invalides
    """
    try:
        return CompareDatasetsUseCase(SqlAlchemyCompareAdapter()).execute(request)
    except InvalidCompareRequestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


class SyncStatusResponse(BaseModel):
    """Etat de la synchronisation CKAN incrementale."""

    ckan_offset: int
    updated_at: str | None


@api_router.get("/internal/sync/status", response_model=SyncStatusResponse)
def internal_sync_status() -> SyncStatusResponse:
    """Retourne l'offset courant de la synchronisation CKAN incrementale.

    Permet de superviser la progression du chargement du catalogue
    opendata.swiss (~10 000+ datasets) sans acceder a la base de donnees.
    """
    repository = SqlAlchemyCacheRepository()
    raw_offset = repository.get_sync_state("ckan_offset")
    ckan_offset = int(raw_offset) if raw_offset and raw_offset.isdigit() else 0

    # Recupere l'horodatage via le port repository (ADR-003, PDS-45)
    updated_at = repository.get_sync_state_updated_at("ckan_offset")

    return SyncStatusResponse(ckan_offset=ckan_offset, updated_at=updated_at)


class SyncMetricsItem(BaseModel):
    """Metriques d'un cycle de sync unique (PDS-45)."""

    id: int
    synced_datasets: int
    synced_organizations: int
    synced_resources: int
    errors: int
    mode: str
    duration_ms: int
    started_at: str
    completed_at: str


class SyncMetricsResponse(BaseModel):
    """Historique des metriques d'ingestion (PDS-45)."""

    items: list[SyncMetricsItem]
    total: int


@api_router.get("/internal/sync/metrics", response_model=SyncMetricsResponse)
def internal_sync_metrics(
    limit: int = Query(20, ge=1, le=100, description="Nombre de cycles recents"),
) -> SyncMetricsResponse:
    """Retourne l'historique des metriques d'ingestion CKAN (PDS-45).

    Permet le pilotage du volume, de la duree et des erreurs d'ingestion.
    Les cycles les plus recents apparaissent en premier.

    Query params:
        limit: Nombre de cycles a retourner (1-100, defaut 20)
    """
    from app.infrastructure.persistence.database import SessionLocal
    from app.infrastructure.persistence.models import SyncMetricsModel

    with SessionLocal() as session:
        total = session.query(SyncMetricsModel).count()
        rows = (
            session.query(SyncMetricsModel).order_by(SyncMetricsModel.id.desc()).limit(limit).all()
        )
        items = [
            SyncMetricsItem(
                id=row.id,
                synced_datasets=row.synced_datasets,
                synced_organizations=row.synced_organizations,
                synced_resources=row.synced_resources,
                errors=row.errors,
                mode=row.mode,
                duration_ms=row.duration_ms,
                started_at=row.started_at,
                completed_at=row.completed_at,
            )
            for row in rows
        ]
        return SyncMetricsResponse(items=items, total=total)


@api_router.post("/internal/sync")
def internal_sync_trigger() -> dict[str, str]:
    """Declenche un cycle de synchronisation CKAN immediat (PDS-52).

    Utilise les memes parametres de lot que le scheduler periodique
    (ckan_sync_max_batches_per_run, ckan_sync_batch_rows, etc.).
    Utile pour forcer un rattrapage sans attendre le prochain cycle horaire.

    Returns:
        Message de confirmation avec le timestamp de declenchement.
    """
    settings = get_settings()
    if not settings.enable_ckan_sync:
        raise HTTPException(
            status_code=503, detail="CKAN sync is disabled (ENABLE_CKAN_SYNC=false)"
        )

    from datetime import UTC, datetime

    logger.info("CKAN sync triggered manually via /internal/sync")
    detect_changes_use_case = DetectChangesUseCase(
        watcher_repository=SqlAlchemyWatcherRepository(),
        changelog_repository=SqlAlchemyChangeLogRepository(),
        cache_repository=SqlAlchemyCacheReadRepository(),
    )
    send_alerts_use_case = SendAlertsUseCase(
        change_log_repository=SqlAlchemyChangeLogRepository(),
        watcher_repository=SqlAlchemyWatcherRepository(),
        cache_repository=SqlAlchemyCacheReadRepository(),
        magic_link_repository=SqlAlchemyMagicLinkRepository(),
        settings=settings,
    )
    use_case = RunSyncCycleUseCase(
        client=CkanHttpClient(),
        repository=SqlAlchemyCacheRepository(),
        settings=settings,
        detect_changes_use_case=detect_changes_use_case,
        send_alerts_use_case=send_alerts_use_case,
    )
    metrics = use_case.execute()

    # Invalidation du cache applicatif apres sync (PDS-46)
    invalidate_cache_after_sync(
        cache=SqlAlchemyQueryCacheRepository(),
        synced_count=int(metrics["synced_datasets"]),
    )
    return {"message": "Sync cycle completed", "triggered_at": datetime.now(UTC).isoformat()}


class CacheStatsResponse(BaseModel):
    """Statistiques de hit/miss du cache applicatif (PDS-46)."""

    hits: int
    misses: int
    stale_entries: int
    total_entries: int
    hit_ratio: float


@api_router.get("/internal/cache/stats", response_model=CacheStatsResponse)
def internal_cache_stats() -> CacheStatsResponse:
    """Retourne les statistiques hit/miss du cache applicatif (PDS-46).

    Permet de mesurer le hit-ratio et les gains de latence du cache
    multi-niveaux. Les compteurs sont cumulatifs depuis le dernier
    redemarrage applicatif ou reset explicite.
    """
    cache = SqlAlchemyQueryCacheRepository()
    stats = cache.get_stats()
    return CacheStatsResponse(
        hits=stats.hits,
        misses=stats.misses,
        stale_entries=stats.stale_entries,
        total_entries=stats.total_entries,
        hit_ratio=round(stats.hit_ratio, 4),
    )


@api_router.post("/internal/cache/reset-stats")
def internal_cache_reset_stats(
    x_internal_token: str | None = Header(None, alias="X-Internal-Token"),
) -> dict[str, str]:
    """Reinitialise les compteurs hit/miss du cache applicatif (PDS-46).

    Protege par un token optionnel (INTERNAL_API_TOKEN). Si le token est
    configure, il doit etre passe dans le header X-Internal-Token.
    Sans token configure, l'endpoint reste ouvert (dev local).
    """
    settings = get_settings()
    if settings.internal_api_token and (
        not x_internal_token or x_internal_token != settings.internal_api_token
    ):
        raise HTTPException(status_code=401, detail="Invalid or missing internal token")
    cache = SqlAlchemyQueryCacheRepository()
    cache.reset_stats()
    return {"message": "Cache stats reset"}


# --- Métriques d'usage (PDS-58) ---


def _verify_internal_token(x_internal_token: str | None) -> None:
    """Verifie le token interne optionnel pour les endpoints /internal/*.

    Si INTERNAL_API_TOKEN est configuré, le header X-Internal-Token
    doit correspondre. Sans token configuré, l'endpoint reste ouvert.
    """
    settings = get_settings()
    if settings.internal_api_token and (
        not x_internal_token or x_internal_token != settings.internal_api_token
    ):
        raise HTTPException(status_code=401, detail="Invalid or missing internal token")


@api_router.get("/internal/metrics/top-queries", response_model=TopQueriesResponse)
def internal_metrics_top_queries(
    limit: int = Query(20, ge=1, le=100, description="Nombre de requetes a retourner"),
    x_internal_token: str | None = Header(None, alias="X-Internal-Token"),
) -> TopQueriesResponse:
    """Retourne les N requetes les plus frequentes, triees par hit_count decroissant (PDS-58).

    Exploite la table query_cache existante (PDS-46) sans infrastructure supplementaire.
    Chaque entree expose la cle de cache, le type d'endpoint, le nombre de hits
    et la date de derniere mise en cache.

    Query params:
        limit: Nombre de requetes a retourner (1-100, defaut 20)
    """
    _verify_internal_token(x_internal_token)
    cache = SqlAlchemyQueryCacheRepository()
    rows = cache.get_top_queries(limit=limit)
    from app.presentation.api.v1.schemas import TopQueryItem

    return TopQueriesResponse(queries=[TopQueryItem(**row) for row in rows])


@api_router.get("/internal/metrics/zero-results", response_model=ZeroResultsResponse)
def internal_metrics_zero_results(
    x_internal_token: str | None = Header(None, alias="X-Internal-Token"),
) -> ZeroResultsResponse:
    """Retourne les requetes dont le response_json contient total=0 (PDS-58).

    Permet d'identifier les recherches infructueuses et les lacunes du catalogue.
    Les entrees avec response_json non parsable sont ignorees.
    """
    _verify_internal_token(x_internal_token)
    cache = SqlAlchemyQueryCacheRepository()
    rows = cache.get_zero_result_queries()
    from app.presentation.api.v1.schemas import ZeroResultItem

    return ZeroResultsResponse(queries=[ZeroResultItem(**row) for row in rows], count=len(rows))


# --- Exploration de ressource (PDS-81/82) ---


@api_router.post("/resources/{resource_id}/explore", response_model=ExploreResourceResponse)
def explore_resource(
    resource_id: str,
    _license_obj: License = Depends(require_license_without_quota_check),  # noqa: B008
) -> ExploreResourceResponse:
    """Explore la structure d'une ressource (CSV/JSON/RDF) via sa clé API.

    Le quota n'est consommé que sur cache miss (pas sur cache hit).
    """

    detail = GetResourceDetailUseCase(SqlAlchemyDatasetDetailAdapter()).execute(resource_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Resource {resource_id} not found")

    # Vérifie que le format est supporté
    supported_formats = [
        "csv",
        "json",
        "rdf",
        "rdf/xml",
        "xml",
        "ttl",
        "turtle",
        "n3",
        "json-ld",
        "jsonld",
    ]
    format_lower = (detail.format or "").lower()
    if format_lower not in supported_formats:
        raise HTTPException(
            status_code=422,
            detail=f"Format '{detail.format}' not supported",
        )

    response = explore_resource_use_case(
        detail=detail,
        cache=SqlAlchemyQueryCacheRepository(),
        ttl_seconds=get_settings().query_cache_ttl_seconds,
    )

    # Consomme le quota uniquement sur cache miss (PDS-109)
    if not response.cached:
        try:
            repository = SqlAlchemyLicenseRepository()
            repository.increment_usage(_license_obj.id)
        except ValueError as e:
            logger.warning(f"License quota exceeded after cache miss: {e}")
            raise HTTPException(
                status_code=429,
                detail="Monthly quota exceeded for this API key",
                headers={
                    "Retry-After": "2592000",  # 30 jours en secondes
                },
            ) from e

    return response

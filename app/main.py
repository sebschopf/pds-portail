import logging
import threading
import traceback
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.application.use_cases.detect_changes import DetectChangesUseCase
from app.application.use_cases.get_health_status import GetHealthStatusUseCase
from app.application.use_cases.invalidate_cache_after_sync import invalidate_cache_after_sync
from app.application.use_cases.run_sync_cycle import RunSyncCycleUseCase
from app.application.use_cases.send_alerts import SendAlertsUseCase
from app.core.config import Settings, get_settings
from app.infrastructure.external.ckan.client import CkanHttpClient
from app.infrastructure.persistence.cache_read_repository import SqlAlchemyCacheReadRepository
from app.infrastructure.persistence.cache_repository import SqlAlchemyCacheRepository
from app.infrastructure.persistence.changelog_repository import SqlAlchemyChangeLogRepository
from app.infrastructure.persistence.database import create_schema
from app.infrastructure.persistence.magic_link_repository import SqlAlchemyMagicLinkRepository
from app.infrastructure.persistence.query_cache_repository import SqlAlchemyQueryCacheRepository
from app.infrastructure.persistence.watcher_repository import SqlAlchemyWatcherRepository
from app.presentation.api.security_headers import SecurityHeadersMiddleware
from app.presentation.api.v1.router import api_router

logger = logging.getLogger(__name__)


def _run_sync_cycle(settings: Settings) -> None:
    """Execute un cycle via le use case deduplication PDS-45 (ADR-003).

    Invalide le cache applicatif apres sync si des datasets ont ete modifies.
    """
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
        synced_count=int(metrics.get("synced_datasets", 0)),
    )


def _start_sync_worker(app: FastAPI, settings: Settings) -> None:
    stop_event = threading.Event()

    def _worker() -> None:
        cache_populated = (
            GetHealthStatusUseCase(SqlAlchemyCacheReadRepository()).execute().cache_populated
        )
        if settings.ckan_sync_bootstrap_if_empty and not cache_populated:
            logger.info("CKAN bootstrap sync triggered (cache empty)")
            try:
                _run_sync_cycle(settings)
            except Exception:  # pragma: no cover - log defensif
                logger.exception("CKAN bootstrap sync failed")

        interval_seconds = max(60, settings.ckan_sync_interval_minutes * 60)
        while not stop_event.wait(interval_seconds):
            try:
                _run_sync_cycle(settings)
            except Exception:  # pragma: no cover - log defensif
                logger.exception("CKAN periodic sync failed")

    worker_thread = threading.Thread(target=_worker, name="ckan-sync-worker", daemon=True)
    worker_thread.start()

    app.state.sync_stop_event = stop_event
    app.state.sync_thread = worker_thread


def _stop_sync_worker(app: FastAPI) -> None:
    stop_event = getattr(app.state, "sync_stop_event", None)
    worker_thread = getattr(app.state, "sync_thread", None)

    if stop_event is not None:
        stop_event.set()
    if worker_thread is not None and worker_thread.is_alive():
        worker_thread.join(timeout=2)


def _build_lifespan(settings: Settings):
    @asynccontextmanager
    async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
        if settings.enable_ckan_sync:
            _start_sync_worker(app=app, settings=settings)
        else:
            logger.info("CKAN sync worker disabled")

        try:
            yield
        finally:
            _stop_sync_worker(app)

    return _lifespan


def create_app() -> FastAPI:
    # Assure que les tables SQLite existent avant les premiers appels API.
    create_schema()
    settings = get_settings()

    docs_url = "/docs" if settings.expose_api_docs else None
    redoc_url = "/redoc" if settings.expose_api_docs else None
    openapi_url = "/api/v1/openapi.json" if settings.expose_api_docs else None

    app = FastAPI(
        title="PDS-Portail Backend",
        version="0.1.0",
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
        lifespan=_build_lifespan(settings),
    )
    # Rate-limiting global via slowapi (PDS-54)
    limiter = Limiter(key_func=get_remote_address, default_limits=["30/minute"])
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
    # Cast requis : slowapi retourne un handler non generique incompatible mypy/strict
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.parsed_cors_allowed_origins,
        allow_origin_regex=settings.cors_allowed_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Security headers (PDS-38, ADR-021)
    app.add_middleware(SecurityHeadersMiddleware, settings=settings)  # type: ignore[arg-type]

    # Exception handler global : loggue la trace complete et garantit que
    # les headers CORS sont presents meme sur les erreurs 500 (PDS-99).
    @app.exception_handler(Exception)
    async def global_exception_handler(  # pyright: ignore[reportUnusedFunction]
        request: Request, exc: Exception
    ) -> PlainTextResponse:
        logger.error(
            "Unhandled exception on %s %s: %s\n%s",
            request.method,
            request.url.path,
            exc,
            traceback.format_exc(),
        )
        return PlainTextResponse("Internal Server Error", status_code=500)

    app.include_router(api_router)
    return app


app = create_app()

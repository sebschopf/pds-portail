import logging
import threading
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.application.use_cases.get_health_status import GetHealthStatusUseCase
from app.application.use_cases.sync_ckan_batch import SyncCkanBatchUseCase
from app.core.config import Settings, get_settings
from app.infrastructure.external.ckan.client import CkanHttpClient
from app.infrastructure.persistence.cache_read_repository import SqlAlchemyCacheReadRepository
from app.infrastructure.persistence.cache_repository import SqlAlchemyCacheRepository
from app.infrastructure.persistence.database import create_schema
from app.presentation.api.v1.router import api_router

logger = logging.getLogger(__name__)


def _cache_is_populated() -> bool:
    snapshot = GetHealthStatusUseCase(SqlAlchemyCacheReadRepository()).execute()
    return snapshot.cache_populated


def _run_sync_cycle(settings: Settings) -> None:
    use_case = SyncCkanBatchUseCase(
        client=CkanHttpClient(),
        repository=SqlAlchemyCacheRepository(),
    )

    total_synced = 0
    for batch_index in range(settings.ckan_sync_max_batches_per_run):
        start = batch_index * settings.ckan_sync_batch_rows
        batch = use_case.execute(start=start, rows=settings.ckan_sync_batch_rows)
        synced_count = len(batch.datasets)
        total_synced += synced_count

        if synced_count < settings.ckan_sync_batch_rows:
            break

        if batch_index < settings.ckan_sync_max_batches_per_run - 1:
            time.sleep(settings.ckan_sync_batch_delay_seconds)

    logger.info("CKAN sync cycle finished: synced_datasets=%s", total_synced)


def _start_sync_worker(app: FastAPI, settings: Settings) -> None:
    stop_event = threading.Event()

    def _worker() -> None:
        if settings.ckan_sync_bootstrap_if_empty and not _cache_is_populated():
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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.parsed_cors_allowed_origins,
        allow_origin_regex=settings.cors_allowed_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)
    return app


app = create_app()

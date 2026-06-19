from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.infrastructure.persistence.database import create_schema
from app.presentation.api.v1.router import api_router


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

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Base declarative commune pour les modeles SQLAlchemy du cache."""


def _ensure_sqlite_directory(database_url: str) -> None:
    sqlite_prefix = "sqlite:///"
    if not database_url.startswith(sqlite_prefix):
        return

    raw_path = database_url.removeprefix(sqlite_prefix)
    if not raw_path or raw_path == ":memory:":
        return

    db_path = Path(raw_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)


settings = get_settings()
_ensure_sqlite_directory(settings.database_url)

engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def create_schema() -> None:
    from app.infrastructure.persistence.models import (
        CacheHitStatsModel,
        DatasetModel,
        FacetsCacheModel,
        OrganizationModel,
        QueryCacheModel,
        ResourceModel,
        SyncMetricsModel,
        SyncStateModel,
    )

    # Reference explicite pour enregistrement SQLAlchemy (side-effect obligatoire)
    _ = (
        CacheHitStatsModel,
        DatasetModel,
        OrganizationModel,
        QueryCacheModel,
        ResourceModel,
        SyncStateModel,
        FacetsCacheModel,
        SyncMetricsModel,
    )

    Base.metadata.create_all(bind=engine)

    # Creer l'index FTS5 pour la recherche full-text (PDS-44).
    # FTS5 n'est pas gere par SQLAlchemy → creation en SQL brut.
    # IF NOT EXISTS evite les erreurs si la table virtuelle existe deja.
    import sqlite3

    from app.core.config import get_settings

    settings = get_settings()
    db_path = settings.database_url.removeprefix("sqlite:///")
    if db_path:
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS datasets_fts USING fts5(
                id, title, description, org_name,
                content='datasets',
                content_rowid='rowid'
            )
            """)
        conn.close()

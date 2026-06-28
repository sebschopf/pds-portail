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


def _migrate_add_source_column() -> None:
    """Ajoute la colonne `source` aux tables existantes (PDS-71).

    SQLAlchemy create_all ne gere pas les migrations de schema (ALTER TABLE).
    On ajoute la colonne en SQL brut si elle n'existe pas deja.
    En SQLite, ALTER TABLE ADD COLUMN avec NOT NULL DEFAULT remplit
    automatiquement les lignes existantes avec la valeur par defaut.
    """
    import logging
    import sqlite3

    logger = logging.getLogger(__name__)
    settings = get_settings()
    db_path = settings.database_url.removeprefix("sqlite:///")
    if not db_path:
        return

    conn = sqlite3.connect(db_path)
    try:
        for table in ("organizations", "datasets", "resources"):
            try:
                conn.execute(
                    f"ALTER TABLE {table} ADD COLUMN source VARCHAR NOT NULL DEFAULT 'ckan'"
                )
                logger.info("Migration PDS-71: colonne source ajoutee a %s", table)
            except sqlite3.OperationalError as exc:
                # La colonne existe deja (duplicate column name) → normal
                if "duplicate column name" in str(exc).lower():
                    logger.debug("Migration PDS-71: colonne source deja presente sur %s", table)
                else:
                    raise
        conn.commit()
    finally:
        conn.close()


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

    # Migration PDS-71 : ajouter la colonne `source` aux tables existantes
    # pour preparer le modele multisource (ckan|i14y|metadata.swiss).
    _migrate_add_source_column()

    # Creer l'index FTS5 pour la recherche full-text (PDS-44, PDS-41).
    # FTS5 n'est pas gere par SQLAlchemy → creation en SQL brut.
    # remove_diacritics=2 supprime les accents automatiquement (FR/DE/IT).
    import sqlite3

    from app.core.config import get_settings

    settings = get_settings()
    db_path = settings.database_url.removeprefix("sqlite:///")
    if db_path:
        conn = sqlite3.connect(db_path)
        # Recréer la table FTS5 avec remove_diacritics=2 (PDS-41: multilingue)
        conn.execute("DROP TABLE IF EXISTS datasets_fts")
        conn.execute("""
            CREATE VIRTUAL TABLE datasets_fts USING fts5(
                id, title, description, org_name,
                tokenize='unicode61 remove_diacritics 2',
                content='datasets',
                content_rowid='rowid'
            )
        """)
        # Triggers pour maintenir l'index FTS5 automatiquement
        conn.executescript("""
            CREATE TRIGGER IF NOT EXISTS datasets_ai AFTER INSERT ON datasets BEGIN
                INSERT INTO datasets_fts(rowid, id, title, description, org_name)
                SELECT new.rowid, new.id, new.title, new.description, org.name
                FROM organizations org WHERE org.id = new.org_id;
            END;

            CREATE TRIGGER IF NOT EXISTS datasets_ad AFTER DELETE ON datasets BEGIN
                INSERT INTO datasets_fts(datasets_fts, rowid, id, title, description, org_name)
                VALUES('delete', old.rowid, old.id, old.title, old.description,
                    (SELECT name FROM organizations WHERE id = old.org_id));
            END;

            CREATE TRIGGER IF NOT EXISTS datasets_au AFTER UPDATE ON datasets BEGIN
                INSERT INTO datasets_fts(datasets_fts, rowid, id, title, description, org_name)
                VALUES('delete', old.rowid, old.id, old.title, old.description,
                    (SELECT name FROM organizations WHERE id = old.org_id));
                INSERT INTO datasets_fts(rowid, id, title, description, org_name)
                SELECT new.rowid, new.id, new.title, new.description, org.name
                FROM organizations org WHERE org.id = new.org_id;
            END;
        """)
        # Backfill initial: indexer les donnees existantes
        conn.execute("""
            INSERT INTO datasets_fts(rowid, id, title, description, org_name)
            SELECT d.rowid, d.id, d.title, d.description, o.name
            FROM datasets d
            JOIN organizations o ON o.id = d.org_id
        """)
        conn.commit()
        conn.close()

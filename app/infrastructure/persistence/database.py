import sqlite3
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

    # Creer/migrer l'index FTS5 pour la recherche full-text (PDS-44, PDS-41, PDS-96).
    # FTS5 n'est pas gere par SQLAlchemy → creation en SQL brut.
    # remove_diacritics=2 supprime les accents automatiquement (FR/DE/IT).
    from app.core.config import get_settings

    settings = get_settings()
    db_path = settings.database_url.removeprefix("sqlite:///")
    if db_path:
        conn = sqlite3.connect(db_path)
        try:
            _ensure_datasets_fts_schema(conn)
            conn.commit()
        finally:
            conn.close()


def _ensure_datasets_fts_schema(conn: "sqlite3.Connection") -> None:
    """Garantit un schema FTS5 coherent avec les colonnes attendues.

    PDS-96 introduit l'indexation des tags. Si un schema historique sans
    `tags` est detecte, on reconstruit table + triggers de maniere controlee
    puis on rejoue un backfill complet.
    """

    existing = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='datasets_fts'"
    ).fetchone()

    if existing is None:
        _create_datasets_fts(conn)
        _create_datasets_fts_triggers(conn)
        _backfill_datasets_fts(conn)
        return

    columns = conn.execute("PRAGMA table_info(datasets_fts)").fetchall()
    column_names = [str(row[1]).lower() for row in columns]
    has_tags = "tags" in column_names

    if has_tags:
        # Schema deja a jour
        return

    _rebuild_datasets_fts_with_tags(conn)


def _rebuild_datasets_fts_with_tags(conn: "sqlite3.Connection") -> None:
    """Reconstruit l'index FTS5 avec la colonne tags (migration PDS-96)."""

    conn.executescript("""
        DROP TRIGGER IF EXISTS datasets_ai;
        DROP TRIGGER IF EXISTS datasets_ad;
        DROP TRIGGER IF EXISTS datasets_au;
        DROP TABLE IF EXISTS datasets_fts;
    """)
    _create_datasets_fts(conn)
    _create_datasets_fts_triggers(conn)
    _backfill_datasets_fts(conn)


def _create_datasets_fts(conn: "sqlite3.Connection") -> None:
    """Cree la table virtuelle FTS5 avec le schema recherche courant."""

    conn.execute("""
        CREATE VIRTUAL TABLE datasets_fts USING fts5(
            id, title, description, tags,
            tokenize='unicode61 remove_diacritics 2',
            content='datasets',
            content_rowid='rowid'
        )
    """)


def _create_datasets_fts_triggers(conn: "sqlite3.Connection") -> None:
    """Cree les triggers FTS5 INSERT/UPDATE/DELETE."""

    conn.executescript("""
        CREATE TRIGGER IF NOT EXISTS datasets_ai AFTER INSERT ON datasets BEGIN
            INSERT INTO datasets_fts(rowid, id, title, description, tags)
            VALUES(new.rowid, new.id, new.title, new.description, new.tags);
        END;

        CREATE TRIGGER IF NOT EXISTS datasets_ad AFTER DELETE ON datasets BEGIN
            INSERT INTO datasets_fts(datasets_fts, rowid, id, title, description, tags)
            VALUES('delete', old.rowid, old.id, old.title, old.description, old.tags);
        END;

        CREATE TRIGGER IF NOT EXISTS datasets_au AFTER UPDATE ON datasets BEGIN
            INSERT INTO datasets_fts(datasets_fts, rowid, id, title, description, tags)
            VALUES('delete', old.rowid, old.id, old.title, old.description, old.tags);
            INSERT INTO datasets_fts(rowid, id, title, description, tags)
            VALUES(new.rowid, new.id, new.title, new.description, new.tags);
        END;
    """)


def _backfill_datasets_fts(conn: "sqlite3.Connection") -> None:
    """Rejoue l'indexation complete des datasets vers FTS5."""

    conn.execute("""
        INSERT INTO datasets_fts(rowid, id, title, description, tags)
        SELECT d.rowid, d.id, d.title, d.description, d.tags
        FROM datasets d
    """)

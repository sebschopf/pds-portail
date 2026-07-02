"""Configuration globale pytest pour tous les tests."""

import os
from collections.abc import Generator

import pytest

import app.infrastructure.persistence.database as persistence_database

# CRITICAL: Ensure all models are registered at module import time
# BEFORE any test file tries to import them. This avoids SQLAlchemy
# forward reference resolution issues with circular imports.
ensure_models_registered_name = "_ensure_models_registered"
ensure_models_registered = getattr(persistence_database, ensure_models_registered_name)
ensure_models_registered()


@pytest.fixture(scope="session", autouse=True)
def setup_database_global() -> Generator[None, None, None]:
    """Initialise le schéma de la base de données UNE SEULE FOIS pour toute la session de tests.

    Fixture pytest automatique (autouse=True) appelée avant tous les tests.
    Crée toutes les tables SQLAlchemy et les indexes, évite les race conditions.
    Cleanup: supprime la BD de test après la session pour isoler les exécutions.
    """
    persistence_database.create_schema()
    yield

    # Cleanup post-session: delete test database file if using SQLite
    # This ensures test isolation between runs (different database state)
    db_url = os.getenv("DATABASE_URL", "sqlite:///./data/app.db")

    # Only cleanup if using SQLite test database (contains "test" or is :memory:)
    if "sqlite:///" in db_url and ("test" in db_url or ":memory:" in db_url):
        try:
            db_path = db_url.removeprefix("sqlite:///")
            if db_path and db_path != ":memory:":
                from pathlib import Path

                Path(db_path).unlink(missing_ok=True)
        except Exception:
            pass  # Cleanup failure is non-critical

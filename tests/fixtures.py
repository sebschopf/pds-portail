"""Fixtures partagées pour tous les tests.

Ce module exporte les fixtures réutilisables pour les tests unitaires
et d'intégration. Elles sont organisées par responsabilité:

- database_session: Session SQLAlchemy avec rollback automatique
- temp_database: BD SQLite temporaire isolée per-test
- mock_http_client: Classe MockTransport httpx pour tests HTTP
"""

from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.infrastructure.persistence.database import SessionLocal, create_schema


@pytest.fixture(scope="function")
def database_session() -> Generator[Session, None, None]:
    """Session SQLAlchemy function-scoped avec rollback automatique.

    Usage:
    ```python
    def test_something(database_session: Session):
        obj = SomeModel(...)
        database_session.add(obj)
        database_session.commit()
        # Auto-rollback on cleanup
    ```

    Avantages:
    - Automatic cleanup via rollback (plus rapide que delete)
    - No manual teardown code needed
    - Changes isolated to test (other tests don't see them)
    - Fails fast on test errors

    Désavantages:
    - Can't test transaction behavior
    - Can't test cascade deletes
    - May hide schema issues (DDL operations)
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
def temp_database(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Generator[Path, None, None]:
    """Temporary SQLite database isolated per test.

    Usage:
    ```python
    def test_schema_migration(temp_database: Path):
        # temp_database is a fresh, empty SQLite file
        # DATABASE_URL env var is set to use it
        from app.infrastructure.persistence.database import create_schema
        create_schema()
        # Test schema migration logic
    ```

    Avantages:
    - Complete test isolation (fresh DB per test)
    - Can test schema migrations
    - Can test cascade deletes
    - No cleanup code needed (auto-deleted with tmp_path)

    Désavantages:
    - Slower (create schema per test)
    - No shared setup across tests in same module
    - More expensive than database_session fixture
    """
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"

    # Override DATABASE_URL for this test
    monkeypatch.setenv("DATABASE_URL", db_url)

    # Create schema in temp database
    create_schema()

    yield db_path

    # Auto-cleanup via tmp_path context manager (no manual delete needed)


@pytest.fixture(scope="function")
def mock_http_client():
    """Return httpx.MockTransport class for HTTP mocking.

    Usage:
    ```python
    import httpx
    from httpx_mock import HTTPXMock

    def test_api_call(mock_http_client):
        with httpx.Client(transport=mock_http_client(...)) as client:
            response = client.get("https://api.example.com/data")
    ```

    Avantages:
    - Fast (no real HTTP calls)
    - Deterministic (no network issues)
    - Easy to test error scenarios

    Note: For complex HTTP mocking, prefer `pytest-httpx` plugin with `httpx_mock` fixture.
    This is a simple reference to the transport class.
    """
    import httpx

    return httpx.MockTransport

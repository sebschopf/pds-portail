from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Base declarative commune pour les modeles SQLAlchemy du cache."""


def _ensure_sqlite_directory(database_url: str) -> None:
    sqlite_prefix = "sqlite:///./"
    if not database_url.startswith(sqlite_prefix):
        return

    relative_path = database_url.removeprefix(sqlite_prefix)
    db_path = Path(relative_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)


settings = get_settings()
_ensure_sqlite_directory(settings.database_url)

engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def create_schema() -> None:
    from app.infrastructure.persistence.models import DatasetModel, OrganizationModel, ResourceModel

    # Reference explicite pour enregistrement SQLAlchemy (side-effect obligatoire)
    _ = (DatasetModel, OrganizationModel, ResourceModel)

    Base.metadata.create_all(bind=engine)

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.persistence.database import Base


class OrganizationModel(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    ckan_url: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)
    last_synced: Mapped[str | None] = mapped_column(String, nullable=True)

    datasets: Mapped[list["DatasetModel"]] = relationship(back_populates="organization")


class DatasetModel(Base):
    __tablename__ = "datasets"
    __table_args__ = (
        Index("idx_datasets_title", "title"),
        Index("idx_datasets_tags", "tags"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)
    created: Mapped[str | None] = mapped_column(String, nullable=True)
    modified: Mapped[str | None] = mapped_column(String, nullable=True)
    quality_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completeness: Mapped[int | None] = mapped_column(Integer, nullable=True)
    freshness_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ckan_url: Mapped[str | None] = mapped_column(String, nullable=True)
    normalized_at: Mapped[str | None] = mapped_column(String, nullable=True)

    organization: Mapped[OrganizationModel] = relationship(back_populates="datasets")
    resources: Mapped[list["ResourceModel"]] = relationship(back_populates="dataset")


class ResourceModel(Base):
    __tablename__ = "resources"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    format: Mapped[str | None] = mapped_column(String, nullable=True)
    url: Mapped[str | None] = mapped_column(String, nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created: Mapped[str | None] = mapped_column(String, nullable=True)
    last_modified: Mapped[str | None] = mapped_column(String, nullable=True)

    dataset: Mapped[DatasetModel] = relationship(back_populates="resources")


class SyncStateModel(Base):
    """Suivi d'etat persistant pour les synchronisations (ex: offset CKAN).

    Stocke des paires cle-valeur avec horodatage de derniere mise a jour.
    Utilise pour reprendre l'ingestion incrementale apres redemarrage.
    """

    __tablename__ = "sync_state"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)


class FacetsCacheModel(Base):
    """Facettes pre-calculees pour eviter les agregations par requete (PDS-44).

    Chaque ligne correspond a une entree de facette (organisation, format, tag).
    Mise a jour apres chaque cycle d'ingestion CKAN.
    """

    __tablename__ = "facets_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    facet_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String, nullable=True)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, configure_mappers, mapped_column, relationship

from app.infrastructure.persistence.database import Base


class OrganizationModel(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    ckan_url: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)
    last_synced: Mapped[str | None] = mapped_column(String, nullable=True)
    source: Mapped[str] = mapped_column(String, nullable=False, default="ckan")

    datasets: Mapped[list["DatasetModel"]] = relationship(
        lambda: DatasetModel,
        back_populates="organization",
    )


class DatasetModel(Base):
    __tablename__ = "datasets"
    __table_args__ = (
        Index("idx_datasets_title", "title"),
        Index("idx_datasets_tags", "tags"),
        # PDS-95 : accelere les filtres par organisation tries par qualite
        Index("idx_datasets_org_quality", "org_id", "quality_score"),
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
    source: Mapped[str] = mapped_column(String, nullable=False, default="ckan")

    organization: Mapped[OrganizationModel] = relationship(
        lambda: OrganizationModel,
        back_populates="datasets",
    )
    resources: Mapped[list["ResourceModel"]] = relationship(
        lambda: ResourceModel,
        back_populates="dataset",
    )


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
    source: Mapped[str] = mapped_column(String, nullable=False, default="ckan")

    dataset: Mapped[DatasetModel] = relationship(
        lambda: DatasetModel,
        back_populates="resources",
    )


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


class SyncMetricsModel(Base):
    """Metriques d'ingestion CKAN pour pilotage et audit (PDS-45).

    Chaque ligne correspond a un cycle de synchronisation termine.
    Permet de suivre le volume, la duree, les erreurs et le mode
    (bootstrap vs differentiel) sur la duree.
    """

    __tablename__ = "sync_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    synced_datasets: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    synced_organizations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    synced_resources: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    errors: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[str] = mapped_column(String, nullable=False)
    completed_at: Mapped[str] = mapped_column(String, nullable=False)


class QueryCacheModel(Base):
    """Cache applicatif multi-niveaux avec TTL et invalidation fine (PDS-46).

    Stocke les réponses d'endpoint sérialisées (JSON) indexées par une clé
    versionnée. Supporte l'invalidation par type d'endpoint et par TTL.
    """

    __tablename__ = "query_cache"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    endpoint_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    response_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    hit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class CacheHitStatsModel(Base):
    """Compteurs hit/miss du cache applicatif pour instrumentation (PDS-46).

    Une seule ligne (id=1) mise à jour atomiquement. Les compteurs sont
    cumulatifs depuis le dernier redémarrage applicatif.
    """

    __tablename__ = "cache_hit_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    hits: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    misses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stale_entries: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class LicenseModel(Base):
    """Licences API pour services payants (exploration, surveillance).

    Chaque licence est associée à une clé API (token opaque UUID v4) hashée en SHA-256.
    Traçabilité : ADR-027 (PDS-80), SPEC-008 §3 & §4.
    """

    __tablename__ = "licenses"
    __table_args__ = (
        Index("idx_licenses_key_hash", "key_hash"),  # Lookup rapide par clé
        Index("idx_licenses_plan", "plan"),  # Filtres par plan (admin)
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    plan: Mapped[str] = mapped_column(String(20), nullable=False)  # 'basic' | 'pro'
    quota_monthly: Mapped[int] = mapped_column(Integer, nullable=False)
    used_this_month: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(String, nullable=False)  # ISO 8601
    expires_at: Mapped[str | None] = mapped_column(String, nullable=True)  # ISO 8601


# Explicit __all__ to ensure the module is fully loaded before any imports
# This helps avoid forward reference resolution issues in SQLAlchemy
__all__ = [
    "OrganizationModel",
    "DatasetModel",
    "ResourceModel",
    "SyncStateModel",
    "FacetsCacheModel",
    "SyncMetricsModel",
    "QueryCacheModel",
    "CacheHitStatsModel",
    "LicenseModel",
]

# Force la configuration des mappers dès l'import du module pour éviter
# les erreurs de résolution tardive des références entre modèles.
configure_mappers()

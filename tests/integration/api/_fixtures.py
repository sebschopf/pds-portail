"""Fixtures partagees pour les tests d'integration API (PDS-46)."""

from __future__ import annotations

import importlib
from typing import Protocol, cast

from fastapi import FastAPI

from app.domain.ckan_normalized import Dataset, NormalizedBatch, Organization, Resource


class DatabaseModulePort(Protocol):
    """Port minimal du module database pour les tests API."""

    def create_schema(self) -> None:
        """Cree le schema SQL local pour les tests."""


class CacheRepositoryPort(Protocol):
    """Port minimal du repository de cache pour injection de fixtures."""

    def upsert_normalized_batch(self, batch: NormalizedBatch) -> None:
        """Persiste un lot normalise dans le cache local."""


def configure_api_modules(
    enable_query_cache: bool = False,
) -> tuple[DatabaseModulePort, CacheRepositoryPort, FastAPI]:
    """Recharge les modules relies a la DB pour les tests de lecture API.

    Par defaut, le cache applicatif PDS-46 est desactive pour eviter de
    polluer les assertions existantes. Les tests specifiques au cache
    passent ``enable_query_cache=True``.
    """
    import os

    import app.core.config as config_module

    config_module.get_settings.cache_clear()

    # Desactiver le cache applicatif PDS-46 pour les tests existants
    if not enable_query_cache:
        os.environ["QUERY_CACHE_ENABLED"] = "false"

    import app.application.use_cases.get_dataset_detail as dataset_detail_use_case_module
    import app.application.use_cases.get_health_status as health_use_case_module
    import app.application.use_cases.get_resource_detail as resource_detail_use_case_module
    import app.application.use_cases.search_datasets as search_datasets_use_case_module
    import app.infrastructure.persistence.cache_read_repository as cache_read_repository_module
    import app.infrastructure.persistence.cache_repository as cache_repository_module
    import app.infrastructure.persistence.compare_adapter as compare_adapter_module
    import app.infrastructure.persistence.database as database_module
    import app.infrastructure.persistence.dataset_detail_adapter as dataset_detail_adapter_module
    import app.infrastructure.persistence.models as models_module
    import app.infrastructure.persistence.query_cache_repository as query_cache_repository_module
    import app.infrastructure.persistence.search_adapter as search_adapter_module
    import app.main as main_module
    import app.presentation.api.v1.router as router_module

    database_module = importlib.reload(database_module)
    models_module = importlib.reload(models_module)
    cache_repository_module = importlib.reload(cache_repository_module)
    cache_read_repository_module = importlib.reload(cache_read_repository_module)
    query_cache_repository_module = importlib.reload(query_cache_repository_module)
    search_adapter_module = importlib.reload(search_adapter_module)
    dataset_detail_adapter_module = importlib.reload(dataset_detail_adapter_module)
    compare_adapter_module = importlib.reload(compare_adapter_module)
    search_datasets_use_case_module = importlib.reload(search_datasets_use_case_module)
    dataset_detail_use_case_module = importlib.reload(dataset_detail_use_case_module)
    resource_detail_use_case_module = importlib.reload(resource_detail_use_case_module)
    health_use_case_module = importlib.reload(health_use_case_module)
    router_module = importlib.reload(router_module)
    main_module = importlib.reload(main_module)

    database_port = cast(DatabaseModulePort, database_module)
    cache_repository = cast(
        CacheRepositoryPort,
        cache_repository_module.SqlAlchemyCacheRepository(),
    )
    app: FastAPI = main_module.app

    return database_port, cache_repository, app


def populate_cache_nominale(cache_repository: CacheRepositoryPort) -> tuple[str, str]:
    """Peuple le cache avec des donnees de test nominales.

    Returns:
        (dataset_id, resource_id) des elements inseres
    """
    org = Organization(
        id="org-001",
        name="Mobilite Urbaine",
        description="Donnees de mobilite",
        ckan_url="https://opendata.swiss/organization/mobilite",
        last_synced="2026-06-13T10:00:00Z",
    )

    resource = Resource(
        id="resource-001",
        dataset_id="dataset-001",
        name="Flux de mobilite CSV",
        format="CSV",
        url="https://opendata.swiss/dataset/mobilite/resource/resource-001/download",
        size_bytes=12345678,
        created="2026-01-01T08:00:00Z",
        last_modified="2026-06-10T15:30:00Z",
    )

    dataset = Dataset(
        id="dataset-001",
        org_id="org-001",
        title="Donnees de mobilite urbaine",
        description="Flux de mobilite collectes dans les zones urbaines, normalises et structures",
        tags=["mobilite", "transports", "urbain", "temps-reel"],
        created="2026-01-01T08:00:00Z",
        modified="2026-06-10T15:30:00Z",
        quality_score=82,
        completeness=88,
        freshness_days=3,
        ckan_url="https://opendata.swiss/dataset/mobilite",
    )

    batch = NormalizedBatch(organizations=[org], datasets=[dataset], resources=[resource])
    cache_repository.upsert_normalized_batch(batch)

    return dataset.id, resource.id


def populate_cache_facets(cache_repository: CacheRepositoryPort) -> None:
    """Peuple le cache avec 2 datasets pour verifier les facettes."""
    org = Organization(
        id="org-001",
        name="Mobilite Urbaine",
        description="Donnees de mobilite",
        ckan_url="https://opendata.swiss/organization/mobilite",
        last_synced="2026-06-13T10:00:00Z",
    )

    dataset_csv = Dataset(
        id="dataset-csv",
        org_id="org-001",
        title="Flux mobilite CSV",
        description="Jeu de donnees mobilite format CSV",
        tags=["mobilite", "open-data"],
        created="2026-01-01T08:00:00Z",
        modified="2026-06-10T15:30:00Z",
        quality_score=80,
        completeness=85,
        freshness_days=4,
    )
    resource_csv = Resource(
        id="resource-csv",
        dataset_id="dataset-csv",
        name="Export CSV",
        format="CSV",
        url="https://example.org/csv",
    )

    dataset_json = Dataset(
        id="dataset-json",
        org_id="org-001",
        title="Flux mobilite JSON",
        description="Jeu de donnees mobilite format JSON",
        tags=["mobilite", "api"],
        created="2026-01-02T08:00:00Z",
        modified="2026-06-11T15:30:00Z",
        quality_score=81,
        completeness=86,
        freshness_days=3,
    )
    resource_json = Resource(
        id="resource-json",
        dataset_id="dataset-json",
        name="Export JSON",
        format="JSON",
        url="https://example.org/json",
    )

    batch = NormalizedBatch(
        organizations=[org],
        datasets=[dataset_csv, dataset_json],
        resources=[resource_csv, resource_json],
    )
    cache_repository.upsert_normalized_batch(batch)


def populate_cache_organizations_many(cache_repository: CacheRepositoryPort) -> None:
    """Peuple >20 organisations pour verifier ordre deterministic + limite facette."""
    organizations: list[Organization] = []
    datasets: list[Dataset] = []
    resources: list[Resource] = []

    for i in range(25):
        org_id = f"org-{i:02d}"
        org_name = f"Org-{i:02d}"
        dataset_id = f"dataset-org-{i:02d}"
        resource_id = f"resource-org-{i:02d}"

        organizations.append(
            Organization(
                id=org_id,
                name=org_name,
                description=f"Organisation {i}",
                ckan_url=f"https://example.org/{org_id}",
                last_synced="2026-06-13T10:00:00Z",
            )
        )
        datasets.append(
            Dataset(
                id=dataset_id,
                org_id=org_id,
                title=f"Dataset {i:02d}",
                description="Dataset de test",
                tags=["test"],
                created="2026-01-01T08:00:00Z",
                modified="2026-06-10T15:30:00Z",
                quality_score=50,
                completeness=50,
                freshness_days=5,
            )
        )
        resources.append(
            Resource(
                id=resource_id,
                dataset_id=dataset_id,
                name=f"Ressource {i:02d}",
                format="CSV",
                url=f"https://example.org/{resource_id}",
            )
        )

    cache_repository.upsert_normalized_batch(
        NormalizedBatch(
            organizations=organizations,
            datasets=datasets,
            resources=resources,
        )
    )

"""Fixtures partagees pour les tests d'integration API (PDS-46)."""

from __future__ import annotations

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
    """Configure un contexte API de test sans rechargement de modules.

    Par defaut, le cache applicatif PDS-46 est desactive pour eviter de
    polluer les assertions existantes. Les tests specifiques au cache
    passent ``enable_query_cache=True``.
    """
    import os

    import app.core.config as config_module
    import app.infrastructure.persistence.cache_repository as cache_repository_module
    import app.infrastructure.persistence.database as database_module
    import app.main as main_module

    # Efface le cache de config pour prendre en compte les variables d'env du test.
    config_module.get_settings.cache_clear()

    # Active/desactive explicitement le cache applicatif pour eviter
    # toute dependance implicite a l'etat des tests precedents.
    os.environ["QUERY_CACHE_ENABLED"] = "true" if enable_query_cache else "false"

    settings = config_module.get_settings()
    database_module.reconfigure_for_test(settings.database_url)

    database_port = cast(DatabaseModulePort, database_module)
    cache_repository = cast(
        CacheRepositoryPort,
        cache_repository_module.SqlAlchemyCacheRepository(),
    )
    app: FastAPI = main_module.create_app()

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


def populate_cache_tag_only_fulltext(cache_repository: CacheRepositoryPort) -> str:
    """Peuple un dataset ou le terme de recherche est present uniquement dans les tags."""

    org = Organization(
        id="org-climat",
        name="Observatoire Donnees",
        description="Donnees environnementales",
        ckan_url="https://opendata.swiss/organization/observatoire",
        last_synced="2026-07-01T10:00:00Z",
    )

    dataset = Dataset(
        id="dataset-tag-only",
        org_id="org-climat",
        title="Mesures annuelles",
        description="Serie chronologique de mesures publiques.",
        tags=["climat", "environnement"],
        created="2026-01-01T08:00:00Z",
        modified="2026-06-10T15:30:00Z",
        quality_score=70,
        completeness=75,
        freshness_days=5,
    )

    resource = Resource(
        id="resource-tag-only",
        dataset_id="dataset-tag-only",
        name="Export CSV",
        format="CSV",
        url="https://example.org/tag-only.csv",
    )

    cache_repository.upsert_normalized_batch(
        NormalizedBatch(organizations=[org], datasets=[dataset], resources=[resource])
    )

    return dataset.id


def populate_cache_multilingual_expansion_case(cache_repository: CacheRepositoryPort) -> str:
    """Peuple un dataset trouvable via expansion multilingue (ex: wetter -> meteo)."""

    org = Organization(
        id="org-meteo",
        name="Meteo Cantonale",
        description="Donnees meteorologiques",
        ckan_url="https://opendata.swiss/organization/meteo",
        last_synced="2026-07-01T10:00:00Z",
    )

    dataset = Dataset(
        id="dataset-multilingual-meteo",
        org_id="org-meteo",
        title="Mesures atmospheriques",
        description="Serie annuelle d'observations.",
        tags=["meteo", "temperature"],
        created="2026-01-01T08:00:00Z",
        modified="2026-06-10T15:30:00Z",
        quality_score=74,
        completeness=78,
        freshness_days=4,
    )

    resource = Resource(
        id="resource-multilingual-meteo",
        dataset_id="dataset-multilingual-meteo",
        name="Export CSV",
        format="CSV",
        url="https://example.org/meteo.csv",
    )

    cache_repository.upsert_normalized_batch(
        NormalizedBatch(organizations=[org], datasets=[dataset], resources=[resource])
    )

    return dataset.id


def populate_cache_facets_filtered_scope_case(
    cache_repository: CacheRepositoryPort,
) -> tuple[str, str]:
    """Peuple 2 datasets pour verifier que les facettes suivent le scope FTS actif."""

    org_temp = Organization(
        id="org-temp",
        name="Observatoire Climat",
        description="Donnees climat",
        ckan_url="https://opendata.swiss/organization/observatoire-climat",
        last_synced="2026-07-01T10:00:00Z",
    )
    org_pop = Organization(
        id="org-pop",
        name="Office Demographie",
        description="Donnees population",
        ckan_url="https://opendata.swiss/organization/office-demographie",
        last_synced="2026-07-01T10:00:00Z",
    )

    ds_temp = Dataset(
        id="dataset-temperature",
        org_id="org-temp",
        title="Temperature annuelle",
        description="Mesures meteorologiques cantonales.",
        tags=["climat", "environnement"],
        created="2026-01-01T08:00:00Z",
        modified="2026-06-10T15:30:00Z",
        quality_score=76,
        completeness=80,
        freshness_days=3,
    )
    ds_pop = Dataset(
        id="dataset-population",
        org_id="org-pop",
        title="Population residente",
        description="Evolution de la population.",
        tags=["population"],
        created="2026-01-01T08:00:00Z",
        modified="2026-06-10T15:30:00Z",
        quality_score=72,
        completeness=79,
        freshness_days=5,
    )

    res_temp = Resource(
        id="resource-temperature",
        dataset_id="dataset-temperature",
        name="Export CSV",
        format="CSV",
        url="https://example.org/temperature.csv",
    )
    res_pop = Resource(
        id="resource-population",
        dataset_id="dataset-population",
        name="Export JSON",
        format="JSON",
        url="https://example.org/population.json",
    )

    cache_repository.upsert_normalized_batch(
        NormalizedBatch(
            organizations=[org_temp, org_pop],
            datasets=[ds_temp, ds_pop],
            resources=[res_temp, res_pop],
        )
    )

    return ds_temp.id, ds_pop.id


def populate_cache_tag_exact_match_case(cache_repository: CacheRepositoryPort) -> tuple[str, str]:
    """Peuple 2 datasets pour verifier le filtrage tag exact (pas sous-chaine)."""

    org = Organization(
        id="org-tags",
        name="Observatoire Qualite Air",
        description="Donnees air et environnement",
        ckan_url="https://opendata.swiss/organization/observatoire-air",
        last_synced="2026-07-01T10:00:00Z",
    )

    ds_air = Dataset(
        id="dataset-air",
        org_id="org-tags",
        title="Qualite de l'air",
        description="Concentrations journalieres.",
        tags=["air"],
        created="2026-01-01T08:00:00Z",
        modified="2026-06-10T15:30:00Z",
        quality_score=77,
        completeness=82,
        freshness_days=2,
    )

    ds_agri = Dataset(
        id="dataset-agri",
        org_id="org-tags",
        title="Statistiques agricoles",
        description="Surfaces agricoles utiles.",
        tags=["agriculture"],
        created="2026-01-01T08:00:00Z",
        modified="2026-06-10T15:30:00Z",
        quality_score=71,
        completeness=76,
        freshness_days=6,
    )

    res_air = Resource(
        id="resource-air",
        dataset_id="dataset-air",
        name="Export CSV",
        format="CSV",
        url="https://example.org/air.csv",
    )
    res_agri = Resource(
        id="resource-agri",
        dataset_id="dataset-agri",
        name="Export CSV",
        format="CSV",
        url="https://example.org/agri.csv",
    )

    cache_repository.upsert_normalized_batch(
        NormalizedBatch(
            organizations=[org],
            datasets=[ds_air, ds_agri],
            resources=[res_air, res_agri],
        )
    )

    return ds_air.id, ds_agri.id


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

"""Tests unitaires de CachedGetDatasetDetailUseCase (PDS-46 — T2)."""

from __future__ import annotations

from typing import cast

import pytest

from app.application.ports.search_repository import DatasetDetailRepositoryPort
from app.application.use_cases.cached_get_dataset_detail import CachedGetDatasetDetailUseCase
from app.presentation.api.v1.schemas import DatasetDetailResponse

from .fakes import FakeCacheRepository


class _FakeDetailRepository:
    """Fake in-memory pour DatasetDetailRepositoryPort."""

    def __init__(self, detail: DatasetDetailResponse | None) -> None:
        self.detail = detail
        self.call_count = 0
        self.last_requested_id: str | None = None

    def get_dataset(self, dataset_id: str) -> DatasetDetailResponse | None:
        self.call_count += 1
        self.last_requested_id = dataset_id
        return self.detail


@pytest.fixture
def sample_detail_response() -> DatasetDetailResponse:
    from app.presentation.api.v1.schemas import DatasetStructure

    return DatasetDetailResponse(
        id="test-dataset-001",
        title="Dataset Test",
        org_name="Org Test",
        description="Un dataset de test",
        quality_score=80,
        completeness=90,
        freshness_days=5,
        tags=["test", "unitaire"],
        resources=[],
        access_modes=[],
        dataset_structure=DatasetStructure(),  # type: ignore[call-arg]
        ckan_url=None,
    )


def test_cache_hit_returns_detail_and_skips_repository(
    sample_detail_response: DatasetDetailResponse,
) -> None:
    """T2e: Un cache hit detail retourne la valeur sans appeler le repository."""
    fake_cache = FakeCacheRepository()
    fake_repo = _FakeDetailRepository(sample_detail_response)

    use_case = CachedGetDatasetDetailUseCase(
        repository=cast(DatasetDetailRepositoryPort, fake_repo),
        cache=fake_cache,
        ttl_seconds=3600,
    )

    # Premier appel: miss
    detail1 = use_case.execute("test-dataset-001")
    assert detail1 is not None
    assert detail1.id == "test-dataset-001"
    assert fake_repo.call_count == 1
    assert len(fake_cache.store) == 1

    # Deuxieme appel: hit
    detail2 = use_case.execute("test-dataset-001")
    assert detail2 is not None
    assert detail2.id == "test-dataset-001"
    assert fake_repo.call_count == 1, "Le repository ne doit pas etre rappele sur cache hit"


def test_cache_miss_calls_repository_and_writes_cache(
    sample_detail_response: DatasetDetailResponse,
) -> None:
    """T2f: Un cache miss appelle le repository et ecrit dans le cache."""
    fake_cache = FakeCacheRepository()
    fake_repo = _FakeDetailRepository(sample_detail_response)

    use_case = CachedGetDatasetDetailUseCase(
        repository=cast(DatasetDetailRepositoryPort, fake_repo),
        cache=fake_cache,
        ttl_seconds=3600,
    )

    assert len(fake_cache.store) == 0
    detail = use_case.execute("test-dataset-001")
    assert detail is not None
    assert fake_repo.call_count == 1
    assert len(fake_cache.store) == 1


def test_not_found_returns_none_without_cache_write() -> None:
    """T2g: Un dataset inexistant retourne None et n'ecrit pas dans le cache."""
    fake_cache = FakeCacheRepository()
    fake_repo = _FakeDetailRepository(None)  # Simule un dataset non trouve

    use_case = CachedGetDatasetDetailUseCase(
        repository=cast(DatasetDetailRepositoryPort, fake_repo),
        cache=fake_cache,
        ttl_seconds=3600,
    )

    detail = use_case.execute("nonexistent-id")
    assert detail is None
    assert fake_repo.call_count == 1
    assert len(fake_cache.store) == 0, "Pas d'ecriture cache si dataset non trouve"


def test_json_decode_error_bypasses_to_repository(
    sample_detail_response: DatasetDetailResponse,
) -> None:
    """T2h: Un JSON invalide dans le cache provoque un bypass."""
    fake_cache = FakeCacheRepository()
    fake_repo = _FakeDetailRepository(sample_detail_response)

    from app.domain.cache_invalidation import build_dataset_detail_cache_key

    key = build_dataset_detail_cache_key("test-dataset-001")
    fake_cache.store[key] = "not valid json at all {{{[]["

    use_case = CachedGetDatasetDetailUseCase(
        repository=cast(DatasetDetailRepositoryPort, fake_repo),
        cache=fake_cache,
        ttl_seconds=3600,
    )

    detail = use_case.execute("test-dataset-001")
    assert detail is not None
    assert fake_repo.call_count == 1, "Le repository doit etre appele malgre le JSON invalide"

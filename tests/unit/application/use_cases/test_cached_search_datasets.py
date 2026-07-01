"""Tests unitaires de CachedSearchDatasetsUseCase (PDS-46 — T2)."""

from __future__ import annotations

from typing import cast

import pytest

from app.application.ports.search_repository import SearchRepositoryPort
from app.application.use_cases.cached_search_datasets import CachedSearchDatasetsUseCase
from app.presentation.api.v1.schemas import SearchResponse

from .fakes import FakeCacheRepository


class _FakeSearchRepository:
    """Fake in-memory pour SearchRepositoryPort."""

    def __init__(self, response: SearchResponse) -> None:
        self.response = response
        self.call_count = 0

    def search(
        self,
        query: str | None = None,
        expanded_terms: list[str] | None = None,
        offset: int = 0,
        limit: int = 20,
        org_filter: str | None = None,
        format_filter: str | None = None,
        tag_filter: str | None = None,
        sort: str = "modified_desc",
    ) -> SearchResponse:
        del (
            query,
            expanded_terms,
            offset,
            limit,
            org_filter,
            format_filter,
            tag_filter,
            sort,
        )  # unused in fake
        self.call_count += 1
        return self.response


@pytest.fixture
def sample_search_response() -> SearchResponse:
    return SearchResponse(
        total=1,
        offset=0,
        limit=20,
        datasets=[],
        facets={"organizations": [], "formats": [], "tags": []},  # type: ignore[arg-type]
    )


def test_cache_hit_returns_cached_value_and_skips_repository(
    sample_search_response: SearchResponse,
) -> None:
    """T2a: Un cache hit retourne la valeur cachee sans appeler le repository."""
    fake_cache = FakeCacheRepository()
    fake_repo = _FakeSearchRepository(sample_search_response)

    use_case = CachedSearchDatasetsUseCase(
        repository=cast(SearchRepositoryPort, fake_repo),
        cache=fake_cache,
        ttl_seconds=3600,
    )

    result1 = use_case.execute(query="test", offset=0, limit=20)
    assert result1.total == 1
    assert fake_repo.call_count == 1
    assert len(fake_cache.store) == 1

    result2 = use_case.execute(query="test", offset=0, limit=20)
    assert result2.total == 1
    assert fake_repo.call_count == 1, "Le repository ne doit pas etre rappele sur cache hit"


def test_cache_miss_calls_repository_and_writes_cache(
    sample_search_response: SearchResponse,
) -> None:
    """T2b: Un cache miss appelle le repository et ecrit le resultat dans le cache."""
    fake_cache = FakeCacheRepository()
    fake_repo = _FakeSearchRepository(sample_search_response)

    use_case = CachedSearchDatasetsUseCase(
        repository=cast(SearchRepositoryPort, fake_repo),
        cache=fake_cache,
        ttl_seconds=3600,
    )

    assert len(fake_cache.store) == 0
    result = use_case.execute(query="test")
    assert result.total == 1
    assert fake_repo.call_count == 1
    assert len(fake_cache.store) == 1, "Le resultat doit etre ecrit dans le cache"


def test_cache_json_decode_error_bypasses_to_repository(
    sample_search_response: SearchResponse,
) -> None:
    """T2c: Un JSON invalide dans le cache provoque un bypass vers le repository."""
    fake_cache = FakeCacheRepository()
    fake_repo = _FakeSearchRepository(sample_search_response)

    from app.domain.cache_invalidation import build_search_cache_key

    key = build_search_cache_key(
        query="test",
        offset=0,
        limit=20,
        org_filter=None,
        format_filter=None,
        tag_filter=None,
        sort="modified_desc",
    )
    fake_cache.store[key] = "not valid json {{{"

    use_case = CachedSearchDatasetsUseCase(
        repository=cast(SearchRepositoryPort, fake_repo),
        cache=fake_cache,
        ttl_seconds=3600,
    )

    result = use_case.execute(query="test")
    assert result.total == 1
    assert fake_repo.call_count == 1, "Le repository doit etre appele malgre le JSON invalide"


def test_different_query_params_produce_different_cache_keys(
    sample_search_response: SearchResponse,
) -> None:
    """T2d: Deux requetes differentes produisent des cles de cache differentes."""
    fake_cache = FakeCacheRepository()
    fake_repo = _FakeSearchRepository(sample_search_response)

    use_case = CachedSearchDatasetsUseCase(
        repository=cast(SearchRepositoryPort, fake_repo),
        cache=fake_cache,
        ttl_seconds=3600,
    )

    use_case.execute(query="mobilite")
    use_case.execute(query="energie")

    assert len(fake_cache.store) == 2, "Deux cles de cache distinctes doivent etre creees"

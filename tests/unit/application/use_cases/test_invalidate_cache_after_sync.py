"""Tests du use case invalidate_cache_after_sync (PDS-106)."""

from __future__ import annotations

import app.core.config as config_module
from app.application.use_cases.invalidate_cache_after_sync import invalidate_cache_after_sync
from app.domain.cache_invalidation import CacheEndpointType, build_dataset_detail_cache_key
from tests.fakes import FakeCacheRepository


def _set_query_cache_enabled(enabled: bool) -> None:
    """Force le flag de cache applicatif dans la configuration lue par le use case."""

    config_module.get_settings.cache_clear()
    config_module.get_settings().query_cache_enabled = enabled


def test_invalidate_cache_after_sync_skips_when_cache_disabled() -> None:
    """Le use case ne touche rien si le cache applicatif est desactive."""

    _set_query_cache_enabled(False)
    cache = FakeCacheRepository()
    search_key = "v2:search:abc123"
    facets_key = "v2:facets:def456"
    detail_key = build_dataset_detail_cache_key("dataset-001")
    cache.store.update({search_key: "search", facets_key: "facets", detail_key: "detail"})

    invalidate_cache_after_sync(
        cache=cache,
        synced_count=3,
        synced_dataset_ids=["dataset-001"],
    )

    assert cache.store == {
        search_key: "search",
        facets_key: "facets",
        detail_key: "detail",
    }
    assert cache.invalidated == []
    config_module.get_settings.cache_clear()


def test_invalidate_cache_after_sync_skips_when_nothing_was_synced() -> None:
    """Aucun dataset synchronise signifie aucune invalidation."""

    _set_query_cache_enabled(True)
    cache = FakeCacheRepository()
    search_key = "v2:search:abc123"
    facets_key = "v2:facets:def456"
    detail_key = build_dataset_detail_cache_key("dataset-001")
    cache.store.update({search_key: "search", facets_key: "facets", detail_key: "detail"})

    invalidate_cache_after_sync(
        cache=cache,
        synced_count=0,
        synced_dataset_ids=["dataset-001"],
    )

    assert cache.store == {
        search_key: "search",
        facets_key: "facets",
        detail_key: "detail",
    }
    assert cache.invalidated == []
    config_module.get_settings.cache_clear()


def test_invalidate_cache_after_sync_invalidates_search_facets_and_dataset_detail() -> None:
    """Les syncs positives invalident SEARCH, FACETS et les details demandes."""

    _set_query_cache_enabled(True)
    cache = FakeCacheRepository()
    search_key = "v2:search:abc123"
    facets_key = "v2:facets:def456"
    detail_key_1 = build_dataset_detail_cache_key("dataset-001")
    detail_key_2 = build_dataset_detail_cache_key("dataset-002")
    untouched_key = "v2:compare:keep-me"
    cache.store.update(
        {
            search_key: "search",
            facets_key: "facets",
            detail_key_1: "detail-1",
            detail_key_2: "detail-2",
            untouched_key: "compare",
        }
    )

    invalidate_cache_after_sync(
        cache=cache,
        synced_count=2,
        synced_dataset_ids=["dataset-001", "dataset-002"],
    )

    assert cache.invalidated == [CacheEndpointType.SEARCH, CacheEndpointType.FACETS]
    assert search_key not in cache.store
    assert facets_key not in cache.store
    assert detail_key_1 not in cache.store
    assert detail_key_2 not in cache.store
    assert cache.store == {untouched_key: "compare"}
    config_module.get_settings.cache_clear()

"""Fakes partagés pour les tests unitaires des use cases (PDS-46, PDS-45).

NOTE: Ce module réexporte depuis tests/fakes.py pour compatibilité rétro.
La source unique de vérité est maintenant tests/fakes.py (centralisé).
"""

# noqa: F401 - imports inutilisés mais exportés pour compatibilité
from tests.fakes import (
    FakeCacheRepository,
    FakeDetailRepository,
    FakeFixedPayloadClient,
    FakeMinimalPayloadClient,
    FakeRateLimitPayloadClient,
    FakeSearchRepository,
    FakeSyncRepository,
    FakeTimeoutPayloadClient,
    SyncCycleTestSettings,
)

__all__ = [
    "FakeCacheRepository",
    "FakeSyncRepository",
    "FakeMinimalPayloadClient",
    "FakeTimeoutPayloadClient",
    "FakeRateLimitPayloadClient",
    "FakeFixedPayloadClient",
    "FakeDetailRepository",
    "FakeSearchRepository",
    "SyncCycleTestSettings",
]


# ────────────────────────────────────────────────────────────────────────────
# LEGACY CLASSES (kept for reference, no longer used)
# ────────────────────────────────────────────────────────────────────────────
# The classes below were moved to tests/fakes.py but are kept here as a comment
# to document where they came from if reverting is needed.
#
# class FakeCacheRepository:
# ────────────────────────────────────────────────────────────────────────────
# LEGACY CLASSES (kept for reference, no longer used)
# ────────────────────────────────────────────────────────────────────────────
# The classes below were moved to tests/fakes.py but are kept here as a comment
# to document where they came from if reverting is needed.
#
# See tests/fakes.py for current implementations:
# - FakeCacheRepository
# - SyncCycleTestSettings
# - FakeSyncRepository
# - FakeMinimalPayloadClient
# - FakeTimeoutPayloadClient
# - FakeRateLimitPayloadClient
# - FakeFixedPayloadClient

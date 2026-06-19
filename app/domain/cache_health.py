"""Objets domaine de lecture pour la sante du cache."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CacheCounts:
    """Compteurs minimaux du cache pour verifier son peuplement."""

    organizations: int
    datasets: int
    resources: int


@dataclass(frozen=True, slots=True)
class CacheHealthSnapshot:
    """Etat de sante lisible expose par les lectures minimales."""

    status: str
    last_sync: str | None
    cache_populated: bool
    counts: CacheCounts

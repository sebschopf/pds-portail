"""Utilitaires de gestion du temps pour des tests déterministes."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

Clock = Callable[[], datetime]


def get_now(clock: Clock | None = None) -> datetime:
    """Retourne l'instant courant en UTC avec clock injectable."""

    now = clock() if clock is not None else datetime.now(UTC)
    if now.tzinfo is None:
        return now.replace(tzinfo=UTC)
    return now.astimezone(UTC)


def iso_at_offset(now: datetime, *, minutes: int = 0) -> str:
    """Construit un timestamp ISO UTC avec un décalage en minutes."""

    return (now + timedelta(minutes=minutes)).astimezone(UTC).isoformat()

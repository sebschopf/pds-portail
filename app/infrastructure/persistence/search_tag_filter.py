"""Filtre tag exact dedie a la recherche."""

from __future__ import annotations

from typing import cast

from sqlalchemy import text, true
from sqlalchemy.sql.elements import ColumnElement


def build_exact_tag_filter(tag_filter: str) -> ColumnElement[bool]:
    """Construit un filtre tag exact (JSON prioritaire, CSV fallback)."""
    normalized = tag_filter.strip().lower()
    if not normalized:
        return true()

    escaped = normalized.replace("'", "''")
    return cast(
        ColumnElement[bool],
        text(
            "(json_valid(datasets.tags) = 1 "
            "AND EXISTS ("
            "SELECT 1 FROM json_each(datasets.tags) AS json_values "
            f"WHERE lower(json_values.value) = '{escaped}'"
            ")) "
            "OR (json_valid(datasets.tags) != 1 "
            f"AND instr(lower(printf(',%s,', coalesce(datasets.tags, ''))), ',{escaped},') > 0)"
        ),
    )

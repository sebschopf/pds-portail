"""Helpers FTS5 dedies a la recherche dataset."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.sql.elements import TextClause


def build_fts_match_clause(query: str) -> TextClause:
    """Construit une clause FTS5 via sous-requete IN."""
    terms = [t.strip() for t in query.split() if t.strip()]
    if not terms:
        return text("1")

    escaped = [escape_fts5_term(t) for t in terms]
    fts_query = " ".join(f'"{t}"' for t in escaped)
    return text(
        "datasets.ROWID IN ("
        "SELECT rowid FROM datasets_fts "
        f"WHERE datasets_fts MATCH '{fts_query}'"
        ")"
    )


def build_fts_match_any_terms_clause(terms: list[str]) -> TextClause:
    """Construit une clause FTS5 en OR pour supporter les termes etendus."""
    normalized = [t.strip() for t in terms if t.strip()]
    if not normalized:
        return text("1")

    escaped = [escape_fts5_term(t) for t in normalized]
    fts_query = " OR ".join(f'"{t}"' for t in escaped)
    return text(
        "datasets.ROWID IN ("
        "SELECT rowid FROM datasets_fts "
        f"WHERE datasets_fts MATCH '{fts_query}'"
        ")"
    )


def escape_fts5_term(term: str) -> str:
    """Echappe les caracteres speciaux de la syntaxe FTS5."""
    return term.replace('"', '""')


def is_fts5_operational_error(exc: OperationalError) -> bool:
    """Detecte les erreurs SQL operatoires liees a FTS5 pour fallback controle."""
    details = str(exc).lower()
    statement = (getattr(exc, "statement", "") or "").lower()
    haystack = f"{details} {statement}"
    markers = (
        "fts5",
        "datasets_fts",
        "match",
        "bm25",
        "no such table",
        "no such function",
        "malformed",
        "unterminated",
        "syntax error",
    )
    return any(marker in haystack for marker in markers)

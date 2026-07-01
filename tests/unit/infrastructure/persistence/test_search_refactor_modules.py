"""Tests unitaires des modules extraits du search adapter (PDS-104)."""

from __future__ import annotations

from typing import Any, cast

from sqlalchemy.dialects import sqlite
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.infrastructure.persistence.search_facets import aggregate_facets
from app.infrastructure.persistence.search_fts import (
    build_fts_match_any_terms_clause,
    build_fts_match_clause,
    is_fts5_operational_error,
)
from app.infrastructure.persistence.search_tag_filter import build_exact_tag_filter


def test_build_fts_match_clause_escapes_quotes() -> None:
    clause = build_fts_match_clause('mobilite "urbaine"')
    sql = str(clause)
    assert "datasets_fts MATCH" in sql
    assert '""urbaine""' in sql


def test_build_fts_match_any_terms_clause_uses_or() -> None:
    clause = build_fts_match_any_terms_clause(["mobilite", "transport"])
    sql = str(clause)
    assert " OR " in sql
    assert '"mobilite"' in sql
    assert '"transport"' in sql


def test_is_fts5_operational_error_detects_fts_markers() -> None:
    fts_exc = OperationalError(
        "SELECT * FROM datasets_fts WHERE datasets_fts MATCH 'unterminated)",
        {},
        Exception("malformed MATCH expression"),
    )
    generic_exc = OperationalError("SELECT 1", {}, Exception("timeout"))

    assert is_fts5_operational_error(fts_exc) is True
    assert is_fts5_operational_error(generic_exc) is False


def test_build_exact_tag_filter_contains_json_and_csv_strategies() -> None:
    expr = build_exact_tag_filter("air")
    sql = str(expr.compile(dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True}))
    assert "json_each" in sql
    assert "json_valid" in sql
    assert "instr" in sql


class _FakeCountQuery:
    def count(self) -> int:
        return 0


class _FakeExecuteResult:
    def all(self) -> list[tuple[Any, ...]]:
        return []


class _FakeScalarsResult:
    def all(self) -> list[str]:
        return []


class _FakeSession:
    def query(self, _model: object) -> _FakeCountQuery:
        return _FakeCountQuery()

    def execute(self, _query: object) -> _FakeExecuteResult:
        return _FakeExecuteResult()

    def scalars(self, _query: object) -> _FakeScalarsResult:
        return _FakeScalarsResult()


def test_aggregate_facets_handles_empty_result_set() -> None:
    session = _FakeSession()
    facets = aggregate_facets(
        session=cast(Session, session),
        base_filters=[],
        format_filter=None,
        fts_where_clause=None,
    )

    assert facets.organizations == []
    assert facets.formats == []
    assert facets.tags == []

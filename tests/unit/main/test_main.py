"""Tests unitaires pour app.main (PDS-107)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.main as main_module
from app.core.config import Settings


class _BootstrapStopEvent:
    def __init__(self) -> None:
        self.wait_calls: list[int] = []
        self.set_called = False

    def wait(self, timeout: int) -> bool:
        self.wait_calls.append(timeout)
        return True

    def set(self) -> None:
        self.set_called = True


class _JoinableStopEvent:
    def __init__(self) -> None:
        self.set_called = False

    def set(self) -> None:
        self.set_called = True


class _ImmediateThread:
    def __init__(self, target: Callable[[], None], name: str, daemon: bool) -> None:
        self.target = target
        self.name = name
        self.daemon = daemon
        self.started = False
        self.join_timeout: float | int | None = None
        self._alive = True

    def start(self) -> None:
        self.started = True
        self.target()
        self._alive = False

    def is_alive(self) -> bool:
        return self._alive

    def join(self, timeout: float | int | None = None) -> None:
        self.join_timeout = timeout
        self._alive = False


class _AliveThread:
    def __init__(self) -> None:
        self.join_timeout: float | int | None = None

    def is_alive(self) -> bool:
        return True

    def join(self, timeout: float | int | None = None) -> None:
        self.join_timeout = timeout


class _FakeHealthStatusUseCase:
    def __init__(self, repository: object) -> None:
        self.repository = repository

    def execute(self) -> SimpleNamespace:
        return SimpleNamespace(cache_populated=False)


def test_start_sync_worker_triggers_bootstrap_and_stores_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Le demarrage du worker lance le bootstrap et expose ses etats."""

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'main-worker.db'}")
    main_module.get_settings.cache_clear()

    run_calls: list[bool] = []
    monkeypatch.setattr(main_module, "GetHealthStatusUseCase", _FakeHealthStatusUseCase)
    monkeypatch.setattr(main_module, "SqlAlchemyCacheReadRepository", lambda: object())
    monkeypatch.setattr(main_module.threading, "Event", _BootstrapStopEvent)
    monkeypatch.setattr(main_module.threading, "Thread", _ImmediateThread)

    def fake_run_sync_cycle(settings: Settings) -> None:
        run_calls.append(settings.enable_ckan_sync)

    monkeypatch.setattr(main_module, "_run_sync_cycle", fake_run_sync_cycle)

    app = FastAPI()
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'main-worker.db'}",
        enable_ckan_sync=True,
        ckan_sync_bootstrap_if_empty=True,
        ckan_sync_interval_minutes=1,
    )

    start_worker_name = "_start_sync_worker"
    start_sync_worker = getattr(main_module, start_worker_name)
    start_sync_worker(app, settings)

    assert run_calls == [True]
    assert isinstance(app.state.sync_stop_event, _BootstrapStopEvent)
    assert isinstance(app.state.sync_thread, _ImmediateThread)
    assert app.state.sync_thread.started is True
    assert app.state.sync_stop_event.wait_calls == [60]


def test_stop_sync_worker_sets_event_and_joins_alive_thread() -> None:
    """L'arret du worker signale l'arret et attend la fin du thread."""

    app = FastAPI()
    stop_event = _JoinableStopEvent()
    worker_thread = _AliveThread()
    app.state.sync_stop_event = stop_event
    app.state.sync_thread = worker_thread

    stop_worker_name = "_stop_sync_worker"
    stop_sync_worker = getattr(main_module, stop_worker_name)
    stop_sync_worker(app)

    assert stop_event.set_called is True
    assert worker_thread.join_timeout == 2


def test_global_exception_handler_returns_500_for_unhandled_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Le handler global convertit une exception interne en reponse 500."""

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'main-exception.db'}")
    monkeypatch.setattr(main_module, "create_schema", lambda: None)
    main_module.get_settings.cache_clear()

    app = main_module.create_app()

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("boom")

    app.add_api_route("/boom", boom)

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/boom")

    assert response.status_code == 500
    assert response.text == "Internal Server Error"

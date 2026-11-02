import pytest

import core.db as db
from core.db import DbError, execute, get_db


@pytest.fixture(autouse=True)
def reset_client(monkeypatch):
    monkeypatch.setattr(db, "_client", None)


def test_get_db_raises_without_connection_string(monkeypatch):
    monkeypatch.setattr(db, "SQLSERVER_CONNECTION_STRING", "")

    with pytest.raises(DbError, match="SQLSERVER_CONNECTION_STRING"):
        get_db()


def test_get_db_creates_and_caches_client(monkeypatch):
    monkeypatch.setattr(db, "SQLSERVER_CONNECTION_STRING", "Driver={x};Server=s;")

    first = get_db()
    second = get_db()

    assert first is second


def test_execute_wraps_client_errors():
    class BrokenQuery:
        def execute(self):
            raise ValueError("boom")

    with pytest.raises(DbError, match="boom"):
        execute(BrokenQuery())


def test_execute_returns_query_result():
    class WorkingQuery:
        def execute(self):
            return "result"

    assert execute(WorkingQuery()) == "result"

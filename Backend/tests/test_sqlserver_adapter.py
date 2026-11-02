from datetime import datetime, timezone

import pytest

import core.db as db
from core.db import DbError, execute, get_db


class FakeCursor:
    def __init__(self, log, rows, columns):
        self.log = log
        self.rows = rows
        self.columns = columns
        self.description = None

    def execute(self, sql, params):
        self.log.append((sql, list(params)))
        self.description = [(c,) for c in self.columns] if self.columns else None

    def fetchall(self):
        return list(self.rows)


class FakeConn:
    def __init__(self, log, rows, columns):
        self.log = log
        self.rows = rows
        self.columns = columns

    def cursor(self):
        return FakeCursor(self.log, self.rows, self.columns)

    def close(self):
        pass


class SqlLog(list):
    state = None


@pytest.fixture
def sql_log(monkeypatch):
    log = SqlLog()
    state = {"rows": [], "columns": []}

    def connect():
        return FakeConn(log, state["rows"], state["columns"])

    monkeypatch.setattr(db, "_connect", connect)
    monkeypatch.setattr(db, "SQLSERVER_CONNECTION_STRING", "Driver={x};Server=s;")
    monkeypatch.setattr(db, "_client", None)
    log.state = state
    return log


def test_select_with_filter_and_limit(sql_log):
    execute(get_db().table("reports").select("id").eq("raw_text", "x").limit(1))
    sql, params = sql_log[-1]
    assert sql == "SELECT TOP (?) [id] FROM [reports] WHERE [raw_text] = ?"
    assert params == [1, "x"]


def test_eq_none_becomes_is_null(sql_log):
    execute(get_db().table("cases").select("*").eq("closed_at", None))
    sql, params = sql_log[-1]
    assert sql == "SELECT * FROM [cases] WHERE [closed_at] IS NULL"
    assert params == []


def test_in_empty_list_matches_nothing(sql_log):
    execute(get_db().table("reports").select("*").in_("id", []))
    assert sql_log[-1][0] == "SELECT * FROM [reports] WHERE 1 = 0"


def test_in_list_uses_placeholders(sql_log):
    execute(get_db().table("reports").select("*").in_("id", [1, 2, 3]))
    sql, params = sql_log[-1]
    assert sql == "SELECT * FROM [reports] WHERE [id] IN (?, ?, ?)"
    assert params == [1, 2, 3]


def test_insert_returns_inserted_row_via_output(sql_log):
    sql_log.state["rows"] = [(7, "gulshan")]
    sql_log.state["columns"] = ["id", "zone_id"]
    result = execute(get_db().table("incidents").insert({"zone_id": "gulshan"}))
    sql, params = sql_log[-1]
    assert sql == "INSERT INTO [incidents] ([zone_id]) OUTPUT INSERTED.* VALUES (?)"
    assert params == ["gulshan"]
    assert result.data == [{"id": 7, "zone_id": "gulshan"}]


def test_update_puts_output_before_where(sql_log):
    execute(get_db().table("cases").update({"status": "approved"}).eq("id", 4))
    sql, params = sql_log[-1]
    assert sql == "UPDATE [cases] SET [status] = ? OUTPUT INSERTED.* WHERE [id] = ?"
    assert params == ["approved", 4]


def test_delete_requires_a_filter(sql_log):
    with pytest.raises(DbError, match="requires a filter"):
        execute(get_db().table("outbox").delete())


def test_delete_not_null_filter(sql_log):
    execute(get_db().table("outbox").delete().not_.is_("id", "null"))
    assert sql_log[-1][0] == "DELETE FROM [outbox] OUTPUT DELETED.* WHERE [id] IS NOT NULL"


def test_upsert_builds_merge_on_conflict_key(sql_log):
    execute(get_db().table("zones").upsert({"id": "johar", "name": "Johar"}, on_conflict="id"))
    sql, params = sql_log[-1]
    assert sql.startswith("MERGE [zones] AS target USING (SELECT ? AS [id], ? AS [name]) AS source ON target.[id] = source.[id]")
    assert "WHEN MATCHED THEN UPDATE SET target.[name] = source.[name]" in sql
    assert sql.endswith("OUTPUT INSERTED.*;")
    assert params == ["johar", "Johar"]


def test_upsert_with_only_key_columns_has_no_matched_branch(sql_log):
    execute(get_db().table("zones").upsert({"id": "johar"}, on_conflict="id"))
    assert "WHEN MATCHED" not in sql_log[-1][0]


def test_json_is_serialised_on_write(sql_log):
    execute(get_db().table("events").insert({"type": "X", "payload": {"a": 1}}))
    assert sql_log[-1][1][1] == '{"a":1}' or sql_log[-1][1][1] == '{"a": 1}'


def test_json_is_parsed_on_read(sql_log):
    sql_log.state["rows"] = [('{"elderly": true}',)]
    sql_log.state["columns"] = ["person_vuln"]
    result = execute(get_db().table("people").select("*"))
    assert result.data == [{"person_vuln": {"elderly": True}}]


def test_iso_timestamps_are_stored_as_naive_utc(sql_log):
    execute(get_db().table("incidents").insert({"first_report_at": "2026-11-03T10:00:00+05:00"}))
    value = sql_log[-1][1][0]
    assert value == datetime(2026, 11, 3, 5, 0, 0)
    assert value.tzinfo is None


def test_datetimes_are_returned_as_utc_iso(sql_log):
    sql_log.state["rows"] = [(datetime(2026, 11, 3, 5, 0, 0),)]
    sql_log.state["columns"] = ["created_at"]
    result = execute(get_db().table("cases").select("*"))
    assert result.data[0]["created_at"] == "2026-11-03T05:00:00+00:00"


def test_bad_identifier_is_rejected(sql_log):
    with pytest.raises(DbError, match="Invalid identifier"):
        execute(get_db().table("cases; DROP TABLE cases").select("*"))


def test_connection_errors_surface_as_dberror(monkeypatch):
    monkeypatch.setattr(db, "SQLSERVER_CONNECTION_STRING", "Driver={x};Server=s;")
    monkeypatch.setattr(db, "_client", None)

    class Boom:
        def cursor(self):
            raise RuntimeError("login failed")

        def close(self):
            pass

    monkeypatch.setattr(db, "_connect", lambda: Boom())
    with pytest.raises(DbError, match="login failed"):
        execute(get_db().table("zones").select("*"))

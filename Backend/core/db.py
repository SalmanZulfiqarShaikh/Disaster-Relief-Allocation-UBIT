from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.config import SQLSERVER_CONNECTION_STRING

logger = logging.getLogger("safezone.db")

_client: Optional["SqlServerClient"] = None

_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$")

JSON_COLUMNS: Dict[str, frozenset] = {
    "zones": frozenset({"boundary_geojson"}),
    "people": frozenset({"person_vuln"}),
    "reports": frozenset({"extraction"}),
    "cases": frozenset({"protocol_path"}),
    "events": frozenset({"payload"}),
    "volunteers": frozenset({"zone_ids", "capabilities"}),
}


class DbError(RuntimeError):
    """Raised when the database is misconfigured or a query fails."""


class Result:
    def __init__(self, data: List[Dict[str, Any]]):
        self.data = data


def _quote(name: str) -> str:
    if not _IDENT_RE.match(name or ""):
        raise DbError(f"Invalid identifier: {name!r}")
    return f"[{name}]"


def _to_db(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, str) and _ISO_RE.match(value):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed
    return value


def _from_db(table: str, column: str, value: Any) -> Any:
    if isinstance(value, str) and column in JSON_COLUMNS.get(table, frozenset()):
        try:
            return json.loads(value)
        except ValueError:
            return value
    if isinstance(value, datetime):
        aware = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
        return aware.isoformat()
    return value


def _connect():
    try:
        import pyodbc
    except ImportError as exc:
        raise DbError("pyodbc is not installed. Run: pip install -r requirements.txt") from exc
    if not SQLSERVER_CONNECTION_STRING:
        raise DbError(
            "SQLSERVER_CONNECTION_STRING must be set. SafeZone has no in-memory fallback database."
        )
    return pyodbc.connect(SQLSERVER_CONNECTION_STRING, autocommit=True, timeout=10)


class _Not:
    def __init__(self, query: "Query"):
        self.query = query

    def is_(self, column: str, value: Any) -> "Query":
        if value != "null" and value is not None:
            raise DbError("only .not_.is_(column, 'null') is supported")
        self.query.not_null.append(column)
        return self.query


class Query:
    def __init__(self, client: "SqlServerClient", table: str):
        self.client = client
        self.table = _quote(table)
        self.raw_table = table
        self.op: Optional[str] = None
        self.select_cols: Optional[List[str]] = None
        self.payload: Dict[str, Any] = {}
        self.conflict: Optional[str] = None
        self.filters: List[tuple] = []
        self.not_null: List[str] = []
        self.in_filter: Optional[tuple] = None
        self.limit_n: Optional[int] = None

    @property
    def not_(self) -> _Not:
        return _Not(self)

    def select(self, *columns: str) -> "Query":
        self.op = "select"
        names = [c.strip() for c in columns if c and c.strip()]
        self.select_cols = None if not names or names == ["*"] else names
        return self

    def insert(self, row: Dict[str, Any]) -> "Query":
        self.op = "insert"
        self.payload = dict(row)
        return self

    def upsert(self, row: Dict[str, Any], on_conflict: Optional[str] = None) -> "Query":
        self.op = "upsert"
        self.payload = dict(row)
        self.conflict = on_conflict
        return self

    def update(self, values: Dict[str, Any]) -> "Query":
        self.op = "update"
        self.payload = dict(values)
        return self

    def delete(self) -> "Query":
        self.op = "delete"
        return self

    def eq(self, column: str, value: Any) -> "Query":
        self.filters.append((column, value))
        return self

    def in_(self, column: str, values) -> "Query":
        self.in_filter = (column, list(values))
        return self

    def limit(self, n: int) -> "Query":
        self.limit_n = int(n)
        return self

    def _where(self):
        parts: List[str] = []
        params: List[Any] = []
        for column, value in self.filters:
            if value is None:
                parts.append(f"{_quote(column)} IS NULL")
            else:
                parts.append(f"{_quote(column)} = ?")
                params.append(_to_db(value))
        for column in self.not_null:
            parts.append(f"{_quote(column)} IS NOT NULL")
        if self.in_filter is not None:
            column, values = self.in_filter
            if not values:
                parts.append("1 = 0")
            else:
                parts.append(f"{_quote(column)} IN ({', '.join('?' for _ in values)})")
                params.extend(_to_db(v) for v in values)
        clause = f" WHERE {' AND '.join(parts)}" if parts else ""
        return clause, params

    def _build(self):
        if self.op == "select":
            cols = "*" if self.select_cols is None else ", ".join(_quote(c) for c in self.select_cols)
            top, params = "", []
            if self.limit_n is not None:
                top, params = "TOP (?) ", [self.limit_n]
            where, where_params = self._where()
            return f"SELECT {top}{cols} FROM {self.table}{where}", params + where_params

        if self.op == "insert":
            cols = list(self.payload)
            if not cols:
                raise DbError("insert needs at least one column")
            sql = (
                f"INSERT INTO {self.table} ({', '.join(_quote(c) for c in cols)}) "
                f"OUTPUT INSERTED.* VALUES ({', '.join('?' for _ in cols)})"
            )
            return sql, [_to_db(self.payload[c]) for c in cols]

        if self.op == "update":
            cols = list(self.payload)
            if not cols:
                raise DbError("update needs at least one column")
            sets = ", ".join(f"{_quote(c)} = ?" for c in cols)
            where, where_params = self._where()
            sql = f"UPDATE {self.table} SET {sets} OUTPUT INSERTED.*{where}"
            return sql, [_to_db(self.payload[c]) for c in cols] + where_params

        if self.op == "delete":
            if not (self.filters or self.in_filter or self.not_null):
                raise DbError("DELETE requires a filter")
            where, where_params = self._where()
            return f"DELETE FROM {self.table} OUTPUT DELETED.*{where}", where_params

        if self.op == "upsert":
            cols = list(self.payload)
            keys = [k.strip() for k in (self.conflict or "id").split(",") if k.strip()]
            if not cols or any(k not in cols for k in keys):
                raise DbError("upsert row must contain its conflict key columns")
            source = ", ".join(f"? AS {_quote(c)}" for c in cols)
            on = " AND ".join(f"target.{_quote(k)} = source.{_quote(k)}" for k in keys)
            others = [c for c in cols if c not in keys]
            matched = ""
            if others:
                sets = ", ".join(f"target.{_quote(c)} = source.{_quote(c)}" for c in others)
                matched = f" WHEN MATCHED THEN UPDATE SET {sets}"
            insert_cols = ", ".join(_quote(c) for c in cols)
            insert_vals = ", ".join(f"source.{_quote(c)}" for c in cols)
            sql = (
                f"MERGE {self.table} AS target USING (SELECT {source}) AS source ON {on}"
                f"{matched} WHEN NOT MATCHED THEN INSERT ({insert_cols}) VALUES ({insert_vals}) "
                f"OUTPUT INSERTED.*;"
            )
            return sql, [_to_db(self.payload[c]) for c in cols]

        raise DbError(f"no operation set on query for {self.raw_table}")

    def execute(self) -> Result:
        sql, params = self._build()
        conn = _connect()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            if cursor.description is None:
                return Result([])
            names = [d[0] for d in cursor.description]
            rows = cursor.fetchall()
        finally:
            conn.close()
        data = [
            {name: _from_db(self.raw_table, name, value) for name, value in zip(names, row)}
            for row in rows
        ]
        return Result(data)


class SqlServerClient:
    def table(self, name: str) -> Query:
        return Query(self, name)


def get_db() -> SqlServerClient:
    global _client
    if _client is not None:
        return _client
    if not SQLSERVER_CONNECTION_STRING:
        raise DbError(
            "SQLSERVER_CONNECTION_STRING must be set. SafeZone has no in-memory fallback database."
        )
    _client = SqlServerClient()
    logger.info("SQL Server client ready")
    return _client


def execute(query: Any):
    try:
        return query.execute()
    except DbError:
        raise
    except Exception as exc:
        raise DbError(f"SQL Server query failed: {exc}") from exc

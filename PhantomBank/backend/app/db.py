"""Small sync database adapter for isolated PostgreSQL databases and unit-test SQLite."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
import sqlite3


class Database:
    def __init__(self, url: str, name: str):
        self.url = url
        self.name = name

    @property
    def is_sqlite(self) -> bool:
        return self.url.startswith("sqlite://")

    @property
    def sqlite_path(self) -> str:
        return self.url.removeprefix("sqlite:///")

    def connect(self):
        if self.is_sqlite:
            if self.sqlite_path != ":memory:":
                Path(self.sqlite_path).parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.sqlite_path, timeout=10, check_same_thread=False)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            return connection

        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:  # pragma: no cover - exercised in deployment, not unit tests
            raise RuntimeError("psycopg is required for PostgreSQL DATABASE_URL values") from exc
        return psycopg.connect(self.url, row_factory=dict_row)

    def adapt(self, sql: str) -> str:
        return sql.replace("?", "%s") if not self.is_sqlite else sql

    def init_schema(self) -> None:
        schema_path = Path(__file__).with_name("schema.sql")
        schema = schema_path.read_text(encoding="utf-8")
        connection = self.connect()
        try:
            if self.is_sqlite:
                connection.executescript(schema)
            else:
                connection.execute(schema)
            connection.commit()
        finally:
            connection.close()

    @contextmanager
    def transaction(self, *, immediate: bool = False) -> Iterator:
        connection = self.connect()
        cursor = connection.cursor()
        try:
            cursor.execute("BEGIN IMMEDIATE" if self.is_sqlite and immediate else "BEGIN")
            yield cursor
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()

    def query(self, sql: str, params: tuple = ()) -> list[dict]:
        connection = self.connect()
        try:
            cursor = connection.cursor()
            cursor.execute(self.adapt(sql), params)
            rows = cursor.fetchall()
            connection.commit()
            return [dict(row) for row in rows]
        finally:
            cursor.close()
            connection.close()

    def fetchone(self, sql: str, params: tuple = ()) -> dict | None:
        connection = self.connect()
        try:
            cursor = connection.cursor()
            cursor.execute(self.adapt(sql), params)
            row = cursor.fetchone()
            connection.commit()
            return dict(row) if row else None
        finally:
            cursor.close()
            connection.close()

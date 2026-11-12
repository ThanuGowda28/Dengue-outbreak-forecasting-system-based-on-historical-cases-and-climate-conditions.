from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from sqlalchemy.engine import Engine


def preserve_corrupt_sqlite_database(engine: Engine) -> Path | None:
    if engine.dialect.name != "sqlite":
        return None

    database = engine.url.database
    if not database or database == ":memory:" or database.startswith("file:"):
        return None

    database_path = Path(database)
    if not database_path.is_file():
        return None

    connection = sqlite3.connect(database_path)
    try:
        results = connection.execute("PRAGMA quick_check").fetchall()
    except sqlite3.DatabaseError as error:
        error_code = getattr(error, "sqlite_errorcode", None)
        if error_code not in {sqlite3.SQLITE_CORRUPT, sqlite3.SQLITE_NOTADB}:
            raise
        results = []
    finally:
        connection.close()

    if results and all(row[0] == "ok" for row in results):
        return None

    backup_path = database_path.with_name(
        f"{database_path.name}.corrupt-{time.time_ns()}.bak"
    )
    database_path.replace(backup_path)
    return backup_path

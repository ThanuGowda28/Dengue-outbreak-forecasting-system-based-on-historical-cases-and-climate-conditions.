import sqlite3
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import URL, text

from backend.app import create_app
from backend.app.extensions import db


class DatabaseBootstrapTests(unittest.TestCase):
    @staticmethod
    def _app(database_path: Path):
        config = type(
            "StartupConfig",
            (),
            {
                "TESTING": False,
                "AUTO_MIGRATE_DATABASE": True,
                "SECRET_KEY": "database-bootstrap-test-secret",
                "JWT_SECRET_KEY": "database-bootstrap-test-jwt-secret",
                "SQLALCHEMY_DATABASE_URI": URL.create(
                    "sqlite", database=str(database_path)
                ),
                "SQLALCHEMY_TRACK_MODIFICATIONS": False,
                "LOAD_PREDICTION_SERVICE": False,
                "CELERY_BROKER_URL": "memory://",
                "CELERY_RESULT_BACKEND": "cache+memory://",
            },
        )
        return create_app(config)

    def _assert_migrated(self, app):
        self.assertFalse(app.logger.disabled)
        with app.app_context():
            try:
                tables = set(
                    db.session.execute(
                        text(
                            "SELECT name FROM sqlite_master "
                            "WHERE type = 'table'"
                        )
                    ).scalars()
                )
                self.assertTrue(
                    {"users", "prediction_history", "forecast_history"}.issubset(
                        tables
                    )
                )
                revision = db.session.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar_one()
                self.assertEqual(revision, "0012_forecast_history")
            finally:
                db.session.remove()
                db.engine.dispose()

    def test_missing_sqlite_database_is_created_and_migrated(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "fresh.sqlite"
            self.assertFalse(database_path.exists())

            app = self._app(database_path)

            self.assertTrue(database_path.is_file())
            self._assert_migrated(app)

    def test_corrupt_sqlite_database_is_preserved_and_recreated(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "corrupt.sqlite"
            database_path.write_bytes(b"not a SQLite database")

            app = self._app(database_path)

            backups = list(
                Path(directory).glob("corrupt.sqlite.corrupt-*.bak")
            )
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_bytes(), b"not a SQLite database")
            self._assert_migrated(app)
            connection = sqlite3.connect(database_path)
            try:
                self.assertEqual(
                    connection.execute("PRAGMA integrity_check").fetchone()[0],
                    "ok",
                )
            finally:
                connection.close()


if __name__ == "__main__":
    unittest.main()

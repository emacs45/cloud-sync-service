import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app


class ServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Path(self.temp_dir.name) / "test.db"
        self.path_patch = patch.object(app, "DATABASE_PATH", self.database)
        self.path_patch.start()
        app.init_database()

    def tearDown(self) -> None:
        self.path_patch.stop()
        self.temp_dir.cleanup()

    def test_items_are_processed_and_updated(self) -> None:
        self.assertEqual(app.save_items([{"id": 7, "title": "  Hallo   Welt  "}]), 1)
        self.assertEqual(app.save_items([{"id": 7, "title": "Neu"}]), 1)

        with app.connect() as db:
            rows = db.execute("SELECT * FROM items").fetchall()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "Neu")
        self.assertEqual(app.serialize(rows[0])["payload"]["id"], 7)


if __name__ == "__main__":
    unittest.main()

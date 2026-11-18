import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("board_app", ROOT / "app.py")
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class BoardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        app.DATABASE = str(Path(self.temp.name) / "board.db")
        app.init_db()

    def test_api_and_server_html_use_same_records(self):
        title = '<img src=x onerror="alert(1)"> Café'
        status, _, _ = app.answer("POST", "/requests", {
            "title": title, "description": "Filming in Berlin", "display_name": "Sarah",
            "skill": "Filming", "status": "In progress", "content_link": ""})
        self.assertEqual(status, 302)
        status, headers, body = app.answer("GET", "/api/requests", {})
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "application/json; charset=utf-8")
        rows = json.loads(body)
        self.assertEqual(rows[0]["title"], title)
        self.assertEqual(rows[0]["status"], "In progress")
        self.assertEqual(set(rows[0]), {"id", "title", "description", "display_name", "skill", "status"})
        status, _, body = app.answer("GET", "/requests", {})
        self.assertEqual(status, 200)
        self.assertIn(b"&lt;img", body)
        self.assertNotIn(b"<img src=x", body)
        self.assertIn(b"board.js?v=7", body)
        self.assertIn(b"request-results", body)
        self.assertEqual(app.answer("POST", "/api/requests", {})[0], 405)

    def test_empty_and_unavailable_database(self):
        self.assertEqual(json.loads(app.answer("GET", "/api/requests", {})[2]), [])
        self.assertIn(b"No requests yet", app.answer("GET", "/requests", {})[2])
        app.DATABASE = str(Path(self.temp.name) / "missing" / "board.db")
        status, headers, body = app.answer("GET", "/api/requests", {})
        self.assertEqual(status, 500)
        self.assertIn("application/json", headers["Content-Type"])
        self.assertIn("error", json.loads(body))

    def test_environment_configuration(self):
        result = subprocess.check_output(
            [sys.executable, "-c", "import app; print(app.HOST, app.PORT)"],
            cwd=ROOT, env={**os.environ, "HOST": "127.0.0.1", "PORT": "8123"}, text=True)
        self.assertEqual(result.strip(), "127.0.0.1 8123")


if __name__ == "__main__":
    unittest.main()

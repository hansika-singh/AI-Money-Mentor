import sys
import unittest
from unittest.mock import MagicMock

# Mock out external libraries that are not installed before importing app
sys.modules['yfinance'] = MagicMock()
sys.modules['groq'] = MagicMock()
sys.modules['pdfplumber'] = MagicMock()

from werkzeug.security import generate_password_hash

from app import app, db, limiter
import app as app_module
from models import User


class TestLoginEmailNotRequired(unittest.TestCase):
    """/login authenticates on username + password only (issue #421)."""

    def setUp(self):
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        # Disable IP rate limiting so it can't mask the behavior under test.
        app.config["RATELIMIT_ENABLED"] = False

        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()

        user = User(
            username="alice",
            email="alice@example.com",
            password_hash=generate_password_hash("s3cret"),
        )
        db.session.add(user)
        db.session.commit()

        limiter.reset()
        app_module._failed_login_attempts.clear()

    def tearDown(self):
        limiter.reset()
        app_module._failed_login_attempts.clear()
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_login_succeeds_without_email(self):
        resp = self.client.post("/login", json={
            "username": "alice",
            "password": "s3cret",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["status"], "success")

    def test_login_ignores_wrong_email(self):
        # A mismatched email no longer affects authentication.
        resp = self.client.post("/login", json={
            "username": "alice",
            "email": "not-her-email@example.com",
            "password": "s3cret",
        })
        self.assertEqual(resp.status_code, 200)

    def test_login_requires_username_and_password(self):
        # Missing password -> 400, and the message no longer mentions email.
        resp = self.client.post("/login", json={"username": "alice"})
        self.assertEqual(resp.status_code, 400)
        self.assertNotIn("email", resp.get_json()["error"].lower())

        # Missing username -> 400.
        resp = self.client.post("/login", json={"password": "s3cret"})
        self.assertEqual(resp.status_code, 400)

    def test_wrong_password_still_rejected(self):
        resp = self.client.post("/login", json={
            "username": "alice",
            "password": "wrong",
        })
        self.assertEqual(resp.status_code, 401)


if __name__ == "__main__":
    unittest.main()

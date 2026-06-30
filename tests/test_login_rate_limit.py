import sys
import unittest
from unittest.mock import MagicMock

# Mock out external libraries that are not installed before importing app
sys.modules['yfinance'] = MagicMock()
sys.modules['groq'] = MagicMock()
sys.modules['pdfplumber'] = MagicMock()

from werkzeug.security import generate_password_hash

from app import app, db, limiter
from app import LOGIN_MAX_FAILED_ATTEMPTS
import app as app_module
from models import User


class TestLoginRateLimitAndLockout(unittest.TestCase):
    """Tests for brute-force protection on the /login route (issue #420)."""

    def setUp(self):
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        app.config["RATELIMIT_ENABLED"] = True

        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()

        # Known user with a real password hash so a correct login can succeed.
        user = User(
            username="victim",
            email="victim@example.com",
            password_hash=generate_password_hash("correct-horse"),
        )
        db.session.add(user)
        db.session.commit()

        # Start every test from a clean slate.
        limiter.reset()
        app_module._failed_login_attempts.clear()

    def tearDown(self):
        limiter.reset()
        app_module._failed_login_attempts.clear()
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _attempt(self, username, password="wrong"):
        return self.client.post("/login", json={
            "username": username,
            "email": f"{username}@example.com",
            "password": password,
        })

    def test_rate_limit_returns_429_after_threshold(self):
        """The 6th request within the window is throttled with 429."""
        # Use distinct usernames so the per-account lockout never triggers;
        # the limiter keys on the client IP, so these all share one bucket.
        for i in range(5):
            resp = self._attempt(f"user{i}")
            self.assertEqual(resp.status_code, 401, f"attempt {i} should be 401")

        resp = self._attempt("user5")
        self.assertEqual(resp.status_code, 429)
        self.assertIn("Too many requests", resp.get_json()["error"])

    def test_account_lockout_after_failed_attempts(self):
        """After N failed attempts for one user, further attempts are locked."""
        # Disable the IP rate limiter so we exercise the lockout path directly.
        app.config["RATELIMIT_ENABLED"] = False

        for i in range(LOGIN_MAX_FAILED_ATTEMPTS):
            resp = self._attempt("victim")
            self.assertEqual(resp.status_code, 401, f"attempt {i} should be 401")

        # Account is now locked: even the correct password is rejected.
        resp = self._attempt("victim", password="correct-horse")
        self.assertEqual(resp.status_code, 429)
        self.assertIn("locked", resp.get_json()["error"].lower())

    def test_successful_login_resets_failed_counter(self):
        """A successful login clears prior failed attempts so no lockout."""
        app.config["RATELIMIT_ENABLED"] = False

        # A few failures, but below the threshold.
        for _ in range(LOGIN_MAX_FAILED_ATTEMPTS - 1):
            self._attempt("victim")

        resp = self._attempt("victim", password="correct-horse")
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("victim", app_module._failed_login_attempts)


if __name__ == "__main__":
    unittest.main()

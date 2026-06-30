import sys
import unittest
from unittest.mock import MagicMock

# Mock out external libraries that are not installed before importing app
sys.modules['yfinance'] = MagicMock()
sys.modules['groq'] = MagicMock()
sys.modules['pdfplumber'] = MagicMock()

from app import app, db, validate_password_strength, PASSWORD_MIN_LENGTH
from models import User


class TestPasswordStrengthHelper(unittest.TestCase):
    """Unit tests for the password strength validator (issue #422)."""

    def test_rejects_short_passwords(self):
        self.assertIsNotNone(validate_password_strength("a"))
        self.assertIsNotNone(validate_password_strength("Abc1"))
        self.assertIsNotNone(validate_password_strength("a" * (PASSWORD_MIN_LENGTH - 1)))

    def test_rejects_missing_letter_or_digit(self):
        self.assertIsNotNone(validate_password_strength("12345678"))   # no letter
        self.assertIsNotNone(validate_password_strength("abcdefgh"))   # no digit

    def test_accepts_strong_password(self):
        self.assertIsNone(validate_password_strength("abcd1234"))
        self.assertIsNone(validate_password_strength("Sup3rSecret"))

    def test_rejects_none(self):
        self.assertIsNotNone(validate_password_strength(None))


class TestRegisterEndpointPasswordStrength(unittest.TestCase):
    """Integration tests for /register enforcing the password policy."""

    def setUp(self):
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_weak_password_rejected_with_400(self):
        resp = self.client.post("/register", json={
            "username": "bob",
            "email": "bob@example.com",
            "password": "a",
        })
        self.assertEqual(resp.status_code, 400)
        # Error message spells out the requirement.
        self.assertIn("8 characters", resp.get_json()["error"])
        # No user should have been created.
        self.assertIsNone(User.query.filter_by(username="bob").first())

    def test_password_without_digit_rejected(self):
        resp = self.client.post("/register", json={
            "username": "bob",
            "email": "bob@example.com",
            "password": "passwordonly",
        })
        self.assertEqual(resp.status_code, 400)

    def test_strong_password_accepted(self):
        resp = self.client.post("/register", json={
            "username": "carol",
            "email": "carol@example.com",
            "password": "Str0ngPass",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIsNotNone(User.query.filter_by(username="carol").first())


if __name__ == "__main__":
    unittest.main()

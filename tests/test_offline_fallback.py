import os
import sys
import json
import pytest

# Unset GROQ_API_KEY from environment to simulate a clean startup without the API key
if "GROQ_API_KEY" in os.environ:
    del os.environ["GROQ_API_KEY"]

# Force clean import by removing cached modules from sys.modules
for mod in ["app", "utils.multi_agent"]:
    if mod in sys.modules:
        del sys.modules[mod]

# Import Flask app and db
from app import app, db


@pytest.fixture
def offline_client():
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.drop_all()


def test_app_starts_offline_without_key():
    """Verify that the global client in app.py is uninitialized (None) when the key is missing."""
    import app as app_module
    assert app_module.client is None


def test_chat_endpoint_fallback(offline_client):
    """Verify that /chat route returns a friendly offline message when client is None."""
    res = offline_client.post("/chat", json={"message": "hello"})
    assert res.status_code == 200
    data = json.loads(res.data)
    assert "reply" in data
    assert "offline" in data["reply"].lower()
    assert "groq_api_key" in data["reply"].lower()


def test_agent_endpoint_fallback(offline_client):
    """Verify that /agent route returns a friendly offline error when client is None."""
    res = offline_client.post("/agent", json={"query": "hello"})
    assert res.status_code == 200
    data = json.loads(res.data)
    assert "error" in data
    assert "offline" in data["error"].lower()
    assert "groq_api_key" in data["error"].lower()


def test_insights_endpoint_fallback(offline_client):
    """Verify that /insights route returns fallback UI card and summary when client is None."""
    res = offline_client.get("/insights")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert "insights" in data
    assert "offline" in data["insights"].lower()
    assert "summary" in data

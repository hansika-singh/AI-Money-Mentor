import json
import pytest
from app import app, db
from models import Asset, Liability

@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.drop_all()

def test_add_and_get_networth(client):
    # Get initial net worth (should be empty/zero)
    res = client.get("/net-worth")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["total_assets"] == 0
    assert data["total_liabilities"] == 0
    assert data["net_worth"] == 0
    assert len(data["assets"]) == 0
    assert len(data["liabilities"]) == 0

    # Add an asset
    res = client.post("/add-asset", json={
        "name": "Savings Account",
        "amount": 50000.0,
        "date": "2026-06-01"
    })
    assert res.status_code == 200
    assert json.loads(res.data)["status"] == "success"

    # Add a liability
    res = client.post("/add-liability", json={
        "name": "Credit Card Bill",
        "amount": 10000.0,
        "date": "2026-06-02"
    })
    assert res.status_code == 200
    assert json.loads(res.data)["status"] == "success"

    # Get updated net worth
    res = client.get("/net-worth")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["total_assets"] == 50000.0
    assert data["total_liabilities"] == 10000.0
    assert data["net_worth"] == 40000.0
    assert len(data["assets"]) == 1
    assert len(data["liabilities"]) == 1
    assert data["assets"][0]["name"] == "Savings Account"
    assert data["assets"][0]["amount"] == 50000.0
    assert data["assets"][0]["date"] == "2026-06-01"
    assert data["liabilities"][0]["name"] == "Credit Card Bill"
    assert data["liabilities"][0]["amount"] == 10000.0
    assert data["liabilities"][0]["date"] == "2026-06-02"

def test_delete_networth_item(client):
    # Add an asset
    client.post("/add-asset", json={"name": "Mutual Funds", "amount": 20000.0})
    
    # Get asset id
    res = client.get("/net-worth")
    data = json.loads(res.data)
    asset_id = data["assets"][0]["id"]
    
    # Delete the asset
    res = client.post("/delete-item", json={
        "type": "asset",
        "id": asset_id
    })
    assert res.status_code == 200
    assert json.loads(res.data)["status"] == "success"

    # Verify asset is deleted
    res = client.get("/net-worth")
    data = json.loads(res.data)
    assert len(data["assets"]) == 0
    assert data["total_assets"] == 0
    assert data["net_worth"] == 0

def test_add_networth_item_default_date(client):
    # Add an asset without date
    res = client.post("/add-asset", json={
        "name": "Cash",
        "amount": 500.0
    })
    assert res.status_code == 200
    
    # Add a liability without date
    res = client.post("/add-liability", json={
        "name": "Friend Debt",
        "amount": 200.0
    })
    assert res.status_code == 200
    
    res = client.get("/net-worth")
    data = json.loads(res.data)
    
    import datetime
    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    
    assert data["assets"][0]["date"] == today
    assert data["liabilities"][0]["date"] == today

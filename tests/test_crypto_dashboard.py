import json
import pytest
from unittest.mock import patch
from app import app, db
from models import CryptoHolding

@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            from models import User
            user = User.query.filter_by(email="test@example.com").first()
            if not user:
                user = User(username="testuser", email="test@example.com", password_hash="pbkdf2:sha256:260000$test")
                db.session.add(user)
                db.session.commit()
            user_id = user.id
            
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user_id)
            sess['_fresh'] = True
            
        yield client
        
        with app.app_context():
            db.drop_all()

@patch("app.get_crypto_price_multi")
def test_create_and_list_crypto_holdings(mock_prices, client):
    # Mock price feed response
    mock_prices.return_value = {
        "BTC": {"USD": 65000.0, "INR": 5400000.0},
        "ETH": {"USD": 3500.0, "INR": 290000.0}
    }

    # 1. Add BTC holding
    res = client.post("/api/crypto/add", json={
        "symbol": "BTC",
        "name": "Bitcoin",
        "quantity": 0.5,
        "buy_price": 60000.0,
        "buy_date": "2026-06-01",
        "currency": "USD",
        "notes": "Test buy BTC"
    })
    assert res.status_code == 200
    assert json.loads(res.data)["success"] is True

    # 2. Add ETH holding
    res = client.post("/api/crypto/add", json={
        "symbol": "ETH",
        "name": "Ethereum",
        "quantity": 2.0,
        "buy_price": 3000.0,
        "buy_date": "2026-06-05",
        "currency": "USD",
        "notes": "Test buy ETH"
    })
    assert res.status_code == 200
    assert json.loads(res.data)["success"] is True

    # 3. Get holdings list
    res = client.get("/api/crypto/list")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["success"] is True
    assert len(data["holdings"]) == 2
    
    # Verify BTC calculations: quantity=0.5, buy=60000, current=65000
    # Invested = 30000, Current = 32500, P&L = 2500
    btc = next(h for h in data["holdings"] if h["symbol"] == "BTC")
    assert btc["invested_value"] == 30000.0
    assert btc["current_value"] == 32500.0
    assert btc["pnl"] == 2500.0
    assert btc["pnl_percent"] == 8.33

    # Verify Summary totals
    summary = data["summary"]
    # Total Invested = 30000 (BTC) + 6000 (ETH) = 36000
    # Total Current = 32500 (BTC) + 7000 (ETH) = 39500
    # Total PnL = 3500
    assert summary["total_invested_usd"] == 36000.0
    assert summary["total_current_usd"] == 39500.0
    assert summary["total_pnl_usd"] == 3500.0


def test_delete_crypto_holding(client):
    # 1. Add holding
    res = client.post("/api/crypto/add", json={
        "symbol": "SOL",
        "name": "Solana",
        "quantity": 10.0,
        "buy_price": 100.0,
        "buy_date": "2026-06-10",
        "currency": "USD"
    })
    assert res.status_code == 200
    
    # Fetch list to find id
    res = client.get("/api/crypto/list")
    holdings = json.loads(res.data)["holdings"]
    sol_id = holdings[0]["id"]

    # 2. Delete holding
    res = client.delete(f"/api/crypto/delete/{sol_id}")
    assert res.status_code == 200
    assert json.loads(res.data)["success"] is True

    # 3. Verify deleted
    res = client.get("/api/crypto/list")
    assert len(json.loads(res.data)["holdings"]) == 0


def test_connect_wallet(client):
    res = client.post("/api/crypto/wallet", json={
        "wallet_address": "0x71C7656EC7ab88b098defB751B7401B5f6d8976F"
    })
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["success"] is True
    assert "portfolio" in data
    assert data["portfolio"]["wallet"] == "0x71C7656EC7ab88b098defB751B7401B5f6d8976F"
    assert len(data["portfolio"]["protocols"]) > 0

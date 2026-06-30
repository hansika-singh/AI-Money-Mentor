import json
import pytest
from unittest.mock import patch
from app import app, db, check_stock_alerts_job
from models import PriceAlert, PriceAlertEvent

def test_create_and_get_price_alerts(client):
    # 1. Create alert
    res = client.post("/api/alerts", json={
        "symbol": "AAPL",
        "target_price": 150.5,
        "condition": "above"
    })
    assert res.status_code == 201
    data = json.loads(res.data)
    assert data["symbol"] == "AAPL"
    assert data["target_price"] == 150.5
    assert data["condition"] == "above"
    assert data["is_triggered"] is False

    # 2. Get alerts
    res = client.get("/api/alerts")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert len(data) == 1
    assert data[0]["symbol"] == "AAPL"

def test_delete_price_alert(client):
    # Create
    res = client.post("/api/alerts", json={
        "symbol": "TCS",
        "target_price": 3000.0,
        "condition": "below"
    })
    alert_id = json.loads(res.data)["id"]

    # Delete
    res = client.delete(f"/api/alerts/{alert_id}")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["status"] == "success"

    # Get should be empty
    res = client.get("/api/alerts")
    assert len(json.loads(res.data)) == 0

def test_check_stock_alerts_job_creates_history_event(client):
    # Create two alerts:
    # 1. AAPL above 150 (triggers if price >= 150)
    # 2. TCS below 3000 (does not trigger if price > 3000)
    client.post("/api/alerts", json={"symbol": "AAPL", "target_price": 150.0, "condition": "above"})
    client.post("/api/alerts", json={"symbol": "TCS", "target_price": 3000.0, "condition": "below"})

    def mock_get_stock_price(symbol):
        if symbol == "AAPL":
            return {"price": 155.0}
        elif symbol == "TCS":
            return {"price": 3100.0}
        return {"error": "not found"}

    with patch("app.get_stock_price", side_effect=mock_get_stock_price):
        check_stock_alerts_job()

    # Verify triggering status + event rows in db
    with app.app_context():
        aapl_alert = PriceAlert.query.filter_by(symbol="AAPL").first()
        tcs_alert = PriceAlert.query.filter_by(symbol="TCS").first()
        assert aapl_alert.is_triggered is True
        assert tcs_alert.is_triggered is False

        events = PriceAlertEvent.query.order_by(PriceAlertEvent.triggered_at.desc()).all()
        assert len(events) == 1
        ev = events[0]
        assert ev.alert_id == aapl_alert.id
        assert ev.symbol == "AAPL"
        assert ev.condition == "above"
        assert ev.price == 155.0


def test_alerts_history_endpoint_and_reset(client):
    # Create two alerts; only one triggers
    client.post("/api/alerts", json={"symbol": "AAPL", "target_price": 150.0, "condition": "above"})
    client.post("/api/alerts", json={"symbol": "TCS", "target_price": 3000.0, "condition": "below"})

    def mock_get_stock_price(symbol):
        if symbol == "AAPL":
            return {"price": 155.0}
        elif symbol == "TCS":
            return {"price": 3100.0}
        return {"error": "not found"}

    with patch("app.get_stock_price", side_effect=mock_get_stock_price):
        check_stock_alerts_job()

    # History should have latest events
    res = client.get("/api/alerts/history?limit=10")
    assert res.status_code == 200
    events = json.loads(res.data)
    assert len(events) == 1
    assert events[0]["symbol"] == "AAPL"

    # Reset should clear triggered flags and delete event rows
    res = client.post("/api/alerts/reset", json={})
    assert res.status_code == 200

    with app.app_context():
        aapl_alert = PriceAlert.query.filter_by(symbol="AAPL").first()
        tcs_alert = PriceAlert.query.filter_by(symbol="TCS").first()
        assert aapl_alert.is_triggered is False
        assert aapl_alert.last_triggered_at is None

        remaining_events = PriceAlertEvent.query.all()
        assert len(remaining_events) == 0


def test_complex_alerts_features(client):
    # 1. Duration Days (consecutive polls checks)
    # Create an alert for AAPL: operator=above, target=150, duration=2
    res = client.post("/api/alerts", json={
        "symbol": "AAPL",
        "target_price": 150.0,
        "operator_type": "above",
        "duration_days": 2,
        "cooldown_days": 0
    })
    assert res.status_code == 201

    # 2. Cooldown Days
    # Create an alert for MSFT: operator=above, target=300, cooldown=1
    res = client.post("/api/alerts", json={
        "symbol": "MSFT",
        "target_price": 300.0,
        "operator_type": "above",
        "duration_days": 0,
        "cooldown_days": 1
    })
    assert res.status_code == 201

    # 3. Crossing conditions
    # Create alerts for TSLA (cross), NVDA (cross_above), GOOG (cross_below)
    client.post("/api/alerts", json={"symbol": "TSLA", "target_price": 200.0, "operator_type": "cross"})
    client.post("/api/alerts", json={"symbol": "NVDA", "target_price": 500.0, "operator_type": "cross_above"})
    client.post("/api/alerts", json={"symbol": "GOOG", "target_price": 100.0, "operator_type": "cross_below"})

    prices_state = {
        "AAPL": 155.0,
        "MSFT": 310.0,
        "TSLA": 190.0,
        "NVDA": 490.0,
        "GOOG": 110.0
    }

    def mock_get_stock_price(symbol):
        return {"price": prices_state.get(symbol, 100.0)}

    with patch("app.get_stock_price", side_effect=mock_get_stock_price):
        # --- Poll 1 ---
        check_stock_alerts_job()

        with app.app_context():
            # AAPL: price 155 >= 150, consecutive_polls should be 1, but is_triggered=False (needs 2)
            aapl = PriceAlert.query.filter_by(symbol="AAPL").first()
            assert aapl.consecutive_polls_met == 1
            assert aapl.is_triggered is False

            # MSFT: price 310 >= 300, triggers immediately (duration=0)
            msft = PriceAlert.query.filter_by(symbol="MSFT").first()
            assert msft.is_triggered is True
            assert msft.last_triggered_at is not None

            # TSLA, NVDA, GOOG: first poll sets last_checked_price but doesn't trigger crossings yet (prev_price was None)
            tsla = PriceAlert.query.filter_by(symbol="TSLA").first()
            nvda = PriceAlert.query.filter_by(symbol="NVDA").first()
            goog = PriceAlert.query.filter_by(symbol="GOOG").first()
            assert tsla.is_triggered is False
            assert nvda.is_triggered is False
            assert goog.is_triggered is False
            assert tsla.last_checked_price == 190.0
            assert nvda.last_checked_price == 490.0
            assert goog.last_checked_price == 110.0

            # Total events: just 1 (MSFT)
            events = PriceAlertEvent.query.all()
            assert len(events) == 1
            assert events[0].symbol == "MSFT"

        # --- Poll 2 (Reset AAPL duration counter on price dip) ---
        prices_state["AAPL"] = 145.0
        # MSFT remains 310, TSLA/NVDA/GOOG cross target prices
        prices_state["TSLA"] = 210.0  # Crossed above 200
        prices_state["NVDA"] = 510.0  # Crossed above 500
        prices_state["GOOG"] = 90.0    # Crossed below 100

        check_stock_alerts_job()

        with app.app_context():
            # AAPL: price dipped below 150, duration reset to 0
            aapl = PriceAlert.query.filter_by(symbol="AAPL").first()
            assert aapl.consecutive_polls_met == 0
            assert aapl.is_triggered is False

            # MSFT: in cooldown, should NOT create another event
            events = PriceAlertEvent.query.filter_by(symbol="MSFT").all()
            assert len(events) == 1

            # TSLA: crossed target, should trigger
            tsla = PriceAlert.query.filter_by(symbol="TSLA").first()
            assert tsla.is_triggered is True

            # NVDA: crossed above, should trigger
            nvda = PriceAlert.query.filter_by(symbol="NVDA").first()
            assert nvda.is_triggered is True

            # GOOG: crossed below, should trigger
            goog = PriceAlert.query.filter_by(symbol="GOOG").first()
            assert goog.is_triggered is True

        # --- Poll 3 (Consecutive poll checks count 1) ---
        prices_state["AAPL"] = 155.0
        check_stock_alerts_job()

        with app.app_context():
            aapl = PriceAlert.query.filter_by(symbol="AAPL").first()
            assert aapl.consecutive_polls_met == 1
            assert aapl.is_triggered is False

        # --- Poll 4 (Consecutive poll checks count 2 -> Triggers!) ---
        prices_state["AAPL"] = 156.0
        check_stock_alerts_job()

        with app.app_context():
            aapl = PriceAlert.query.filter_by(symbol="AAPL").first()
            assert aapl.is_triggered is True
            assert aapl.consecutive_polls_met == 0

        # --- Test Cooldown Expiration ---
        with app.app_context():
            # Manually backdate MSFT's last_triggered_at to 2 days ago (outside 1-day cooldown)
            from datetime import datetime, timedelta
            msft = PriceAlert.query.filter_by(symbol="MSFT").first()
            msft.last_triggered_at = datetime.utcnow() - timedelta(days=2)
            db.session.commit()

        # Run job again: MSFT should trigger a second event
        check_stock_alerts_job()

        with app.app_context():
            events = PriceAlertEvent.query.filter_by(symbol="MSFT").all()
            assert len(events) == 2

        # --- Test Crossing back/reverse directions ---
        # Reset NVDA/GOOG alerts triggered flags & set last checked prices to test crossing back
        with app.app_context():
            nvda = PriceAlert.query.filter_by(symbol="NVDA").first()
            nvda.is_triggered = False
            nvda.last_checked_price = 510.0

            goog = PriceAlert.query.filter_by(symbol="GOOG").first()
            goog.is_triggered = False
            goog.last_checked_price = 90.0

            tsla = PriceAlert.query.filter_by(symbol="TSLA").first()
            tsla.is_triggered = False
            tsla.last_checked_price = 210.0

            db.session.commit()

        # Prices cross in reverse: TSLA dips (cross), NVDA dips (cross below), GOOG rises (cross above)
        prices_state["TSLA"] = 190.0  # Crossed below 200
        prices_state["NVDA"] = 490.0  # Crossed below 500 (NVDA is cross_above)
        prices_state["GOOG"] = 110.0  # Crossed above 100 (GOOG is cross_below)

        check_stock_alerts_job()

        with app.app_context():
            # TSLA: operator=cross, so crossing below should trigger
            tsla = PriceAlert.query.filter_by(symbol="TSLA").first()
            assert tsla.is_triggered is True

            # NVDA: operator=cross_above, so crossing below should NOT trigger
            nvda = PriceAlert.query.filter_by(symbol="NVDA").first()
            assert nvda.is_triggered is False

            # GOOG: operator=cross_below, so crossing above should NOT trigger
            goog = PriceAlert.query.filter_by(symbol="GOOG").first()
            assert goog.is_triggered is False


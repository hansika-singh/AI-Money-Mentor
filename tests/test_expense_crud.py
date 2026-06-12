import json
import pytest
from app import app, db
from models import Expense

@pytest.fixture
def client():
    # Save existing expenses using ORM to prevent SQLite file I/O locks
    with app.app_context():
        db.create_all()
        saved_expenses = [
            {
                "id": e.id,
                "category": e.category,
                "amount": e.amount,
                "date": e.date,
                "ai_confidence": e.ai_confidence,
                "user_corrected": e.user_corrected,
                "original_ai_category": e.original_ai_category,
                "is_subscription": e.is_subscription,
                "is_recurring": e.is_recurring,
                "is_anomaly": e.is_anomaly,
                "merchant_name": e.merchant_name
            }
            for e in Expense.query.all()
        ]
        db.session.query(Expense).delete()
        db.session.commit()
        
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client
        
    # Restore the database state
    with app.app_context():
        db.session.query(Expense).delete()
        for data in saved_expenses:
            e = Expense()
            e.id = data["id"]
            e.category = data["category"]
            e.amount = data["amount"]
            e.date = data["date"]
            e.ai_confidence = data["ai_confidence"]
            e.user_corrected = data["user_corrected"]
            e.original_ai_category = data["original_ai_category"]
            e.is_subscription = data["is_subscription"]
            e.is_recurring = data["is_recurring"]
            e.is_anomaly = data["is_anomaly"]
            e.merchant_name = data["merchant_name"]
            db.session.add(e)
        db.session.commit()

def test_expense_crud_operations(client):
    # 1. Create an expense via add_expense
    res = client.post("/add_expense", json={
        "category": "Food",
        "amount": 250.0,
        "date": "2026-06-10"
    })
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["status"] == "success"

    # Verify database has it
    with app.app_context():
        expense = Expense.query.first()
        assert expense is not None
        assert expense.category == "Food"
        assert expense.amount == 250.0
        assert expense.date == "2026-06-10"
        expense_id = expense.id

    # 2. Update the expense (PUT)
    res = client.put(f"/expense/{expense_id}", json={
        "category": "Travel",
        "amount": 300.0,
        "date": "2026-06-11"
    })
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["status"] == "success"
    assert data["expense"]["category"] == "Travel"
    assert data["expense"]["amount"] == 300.0
    assert data["expense"]["date"] == "2026-06-11"
    assert data["expense"]["user_corrected"] is True

    # Verify DB has new values
    with app.app_context():
        expense = Expense.query.get(expense_id)
        assert expense.category == "Travel"
        assert expense.amount == 300.0
        assert expense.date == "2026-06-11"
        assert expense.user_corrected is True
        assert expense.original_ai_category == "Food"

    # 3. Update without changing category (user_corrected shouldn't reset)
    res = client.put(f"/expense/{expense_id}", json={
        "amount": 350.0
    })
    assert res.status_code == 200
    with app.app_context():
        expense = Expense.query.get(expense_id)
        assert expense.category == "Travel"
        assert expense.amount == 350.0
        assert expense.user_corrected is True

    # 4. Delete the expense (DELETE)
    res = client.delete(f"/expense/{expense_id}")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["status"] == "success"

    # Verify DB is empty
    with app.app_context():
        expense = Expense.query.get(expense_id)
        assert expense is None

def test_expense_crud_not_found(client):
    res = client.put("/expense/9999", json={"amount": 10.0})
    assert res.status_code == 404
    
    res = client.delete("/expense/9999")
    assert res.status_code == 404

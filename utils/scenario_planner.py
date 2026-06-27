import math
from datetime import datetime
from models import User, Expense, Asset, Liability, db
from utils.fire_planner import FIREPlanner
from utils.financial_predictor import FinancialPredictor

def get_user_snapshot(user_id: int):
    """Collect current financial state for a user.
    Returns a dict with income, expenses, assets, liabilities, net_worth.
    """
    # Simplified aggregation – adjust as needed for real data
    income = sum(e.amount for e in Expense.query.filter_by(user_id=user_id, category='Income'))
    expenses = sum(e.amount for e in Expense.query.filter(Expense.user_id == user_id, Expense.category != 'Income'))
    assets = sum(a.current_value for a in Asset.query.filter_by(user_id=user_id))
    liabilities = sum(l.current_balance for l in Liability.query.filter_by(user_id=user_id))
    return {
        "income": income,
        "expenses": expenses,
        "assets": assets,
        "liabilities": liabilities,
        "net_worth": assets - liabilities,
    }

def job_change(snapshot: dict, salary_delta: float) -> dict:
    """Apply a salary change represented as a decimal (e.g., 0.20 for +20%)."""
    snapshot["income"] = round(snapshot["income"] * (1 + salary_delta), 2)
    return snapshot

def new_loan(snapshot: dict, amount: float, interest: float, tenure_years: int) -> dict:
    """Add a new loan liability to the snapshot.
    The function only updates the liabilities total; amortization details can be added later.
    """
    snapshot["liabilities"] = round(snapshot["liabilities"] + amount, 2)
    return snapshot

def add_child(snapshot: dict, additional_cost: float) -> dict:
    """Add an estimated annual cost for a new child to expenses."""
    snapshot["expenses"] = round(snapshot["expenses"] + additional_cost, 2)
    return snapshot

def project_snapshot(snapshot: dict, years: int = 30) -> dict:
    """Run long‑term projection using existing predictor utilities.
    Returns projected balance and a FIRE retirement plan summary.
    """
    # Build a simple cash‑flow series for the predictor
    transactions = []
    for year in range(years):
        cash_flow = snapshot["income"] - snapshot["expenses"]
        transactions.append({
            "date": datetime.utcnow().replace(year=datetime.utcnow().year + year),
            "amount": cash_flow,
            "category": "CashFlow",
        })
    predictor = FinancialPredictor()
    future = predictor.predict_balance(
        income=snapshot["income"],
        balance=snapshot["net_worth"],
        transactions=transactions,
        days=years * 365,
    )
    fire = FIREPlanner(
        current_age=30,
        retirement_age=55,
        annual_expenses=snapshot["expenses"],
        current_corpus=snapshot["net_worth"],
        monthly_savings=(snapshot["income"] - snapshot["expenses"]) / 12,
    )
    fire_plan = fire.get_plan_summary()
    return {
        "future_balance": future,
        "fire_plan": fire_plan,
    }

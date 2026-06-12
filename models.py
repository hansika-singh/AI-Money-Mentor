"""Database models and persistence layer for AI-Money-Mentor.

Replaces the previous module-level in-memory lists (expense_data,
assets_data, liabilities_data) with SQLite-backed storage via
Flask-SQLAlchemy, so data survives server restarts.
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Portfolio(db.Model):
    __tablename__ = "portfolio"
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    buy_price = db.Column(db.Float, nullable=False)
    buy_date = db.Column(db.String(40), nullable=False)
    investment_type = db.Column(db.String(20), default="stock")
    notes = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self, current_price=None):
        current_price = current_price or self.buy_price
        current_value = self.quantity * current_price
        invested_value = self.quantity * self.buy_price
        pnl = current_value - invested_value
        pnl_percent = (pnl / invested_value * 100) if invested_value > 0 else 0
        
        return {
            "id": self.id,
            "symbol": self.symbol,
            "name": self.name,
            "quantity": self.quantity,
            "buy_price": self.buy_price,
            "buy_date": self.buy_date,
            "current_price": current_price,
            "current_value": round(current_value, 2),
            "invested_value": round(invested_value, 2),
            "pnl": round(pnl, 2),
            "pnl_percent": round(pnl_percent, 2),
            "investment_type": self.investment_type
        }


class PriceAlert(db.Model):
    __tablename__ = "price_alerts"
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), nullable=False)
    target_price = db.Column(db.Float, nullable=False)
    condition = db.Column(db.String(10), default="above")
    is_triggered = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Diagnostics + UI info
    last_check_error = db.Column(db.String(500), nullable=True)
    last_triggered_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "symbol": self.symbol,
            "target_price": self.target_price,
            "condition": self.condition,
            "is_triggered": self.is_triggered,
            "last_check_error": self.last_check_error,
            "last_triggered_at": self.last_triggered_at.isoformat() if self.last_triggered_at else None,
        }


class PriceAlertEvent(db.Model):
    __tablename__ = "price_alert_events"
    id = db.Column(db.Integer, primary_key=True)

    alert_id = db.Column(db.Integer, nullable=False, index=True)
    triggered_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Price snapshot at the moment of trigger
    price = db.Column(db.Float, nullable=False)

    # Store condition + symbol for easier querying/debugging
    condition = db.Column(db.String(10), nullable=False)
    symbol = db.Column(db.String(20), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "alert_id": self.alert_id,
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
            "price": self.price,
            "condition": self.condition,
            "symbol": self.symbol,
        }


class Expense(db.Model):
    __tablename__ = "expenses"
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.String(40), nullable=False)
    
    # New AI fields
    ai_confidence = db.Column(db.Float, default=0.0)
    user_corrected = db.Column(db.Boolean, default=False)
    original_ai_category = db.Column(db.String(120), nullable=True)
    is_subscription = db.Column(db.Boolean, default=False)
    is_recurring = db.Column(db.Boolean, default=False)
    is_anomaly = db.Column(db.Boolean, default=False)
    merchant_name = db.Column(db.String(200), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "amount": self.amount,
            "date": self.date,
            "ai_confidence": self.ai_confidence,
            "user_corrected": self.user_corrected,
            "is_subscription": self.is_subscription,
            "is_recurring": self.is_recurring,
            "is_anomaly": self.is_anomaly
        }


class Asset(db.Model):
    __tablename__ = "assets"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.String(40), nullable=False, default=lambda: datetime.utcnow().strftime("%Y-%m-%d"))

    def to_dict(self):
        # Returns the real database primary key so /delete-item can look up the
        # row by stable PK rather than by positional list index. Using a
        # positional index was the root cause of the negative-index silent
        # deletion and out-of-range IndexError bugs (issue #125).
        return {"id": self.id, "name": self.name, "amount": self.amount, "date": self.date}


class Liability(db.Model):
    __tablename__ = "liabilities"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.String(40), nullable=False, default=lambda: datetime.utcnow().strftime("%Y-%m-%d"))

    def to_dict(self):
        # Same fix as Asset.to_dict -- returns the real PK, not a list index.
        return {"id": self.id, "name": self.name, "amount": self.amount, "date": self.date}


class BudgetLimit(db.Model):
    __tablename__ = "budget_limits"
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(120), unique=True, nullable=False)
    limit_amount = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "limit_amount": self.limit_amount
        }


class BudgetAlert(db.Model):
    __tablename__ = "budget_alerts"
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(120), nullable=False)
    year_month = db.Column(db.String(7), nullable=False)  # e.g., "2026-06"
    threshold = db.Column(db.Integer, nullable=False)    # 80, 90, or 100
    triggered_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "year_month": self.year_month,
            "threshold": self.threshold,
            "triggered_at": self.triggered_at.isoformat()
        }


class FinancialGoal(db.Model):
    __tablename__ = "financial_goals"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    target_amount = db.Column(db.Float, nullable=False)
    current_amount = db.Column(db.Float, nullable=False, default=0.0)
    target_date = db.Column(db.String(10), nullable=False)  # YYYY-MM

    # Optional AI-generated plan/tactics
    ai_milestone_tactics = db.Column(db.Text, nullable=True)  # plain text, 3-5 bullet points
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        progress_percent = (self.current_amount / self.target_amount * 100) if self.target_amount > 0 else 0
        return {
            "id": self.id,
            "name": self.name,
            "target_amount": self.target_amount,
            "current_amount": self.current_amount,
            "progress_percent": round(progress_percent, 2),
            "target_date": self.target_date,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class RecurringExpense(db.Model):
    __tablename__ = "recurring_expenses"

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)

    # Stored as YYYY-MM-DD (strings) to keep the model consistent with existing Expense.date usage
    start_date = db.Column(db.String(40), nullable=False)

    frequency = db.Column(db.String(20), nullable=False)  # monthly|weekly|yearly
    active = db.Column(db.Boolean, default=True)

    # Optional end date (YYYY-MM-DD)
    end_date = db.Column(db.String(40), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "amount": self.amount,
            "start_date": self.start_date,
            "frequency": self.frequency,
            "active": self.active,
            "end_date": self.end_date,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------- WEEKLY DIGEST (Scheduled AI) ----------------
class DigestPreference(db.Model):
    """Single-row preference store (no user table in current app)."""
    __tablename__ = "digest_preferences"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), nullable=True)
    enable_weekly_digest = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WeeklyDigestLog(db.Model):
    __tablename__ = "weekly_digest_logs"
    id = db.Column(db.Integer, primary_key=True)
    period_start = db.Column(db.DateTime, nullable=False)
    period_end = db.Column(db.DateTime, nullable=False)

    sent_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(30), nullable=False, default="scheduled")  # scheduled|sent|failed|done
    digest_text = db.Column(db.Text, nullable=True)
    ai_used = db.Column(db.Boolean, default=False)

    snapshot_net_worth_start = db.Column(db.Float, nullable=True)
    snapshot_net_worth_end = db.Column(db.Float, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('period_start', 'period_end', name='uq_weekly_digest_period'),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "status": self.status,
            "digest_text": self.digest_text,
            "ai_used": self.ai_used,
            "snapshot_net_worth_start": self.snapshot_net_worth_start,
            "snapshot_net_worth_end": self.snapshot_net_worth_end,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


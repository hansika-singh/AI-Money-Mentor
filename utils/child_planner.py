import math
from datetime import datetime
from models import ChildGoal, db
from utils.goal_investment_planner import GoalInvestmentPlanner

__all__ = ['project_future_cost', 'estimate_required_sip', 'suggest_investments']


def project_future_cost(current_cost: float, years: int, inflation: float = 0.05) -> float:
    """Calculate projected cost after given years with annual inflation.
    Uses compound interest formula: FV = PV * (1 + r) ** n
    """
    if years < 0:
        raise ValueError('Years must be non‑negative')
    return round(current_cost * ((1 + inflation) ** years), 2)


def estimate_required_sip(projected_cost: float, years: int, target_corpus: float = 0.0) -> float:
    """Estimate monthly SIP required to reach `projected_cost` in `years`.
    A simple SIP formula is used:
        SIP = FV / (((1 + r) ** n - 1) / r)
    where r is the assumed monthly return (e.g., 0.006 = ~7.2% annual).
    """
    if years <= 0:
        raise ValueError('Years must be positive')
    # Assume a modest annual return of 7% -> monthly rate ~0.0056
    monthly_rate = 0.0056
    months = years * 12
    denominator = ((1 + monthly_rate) ** months - 1) / monthly_rate
    sip = (projected_cost - target_corpus) / denominator
    return round(sip, 2)


def suggest_investments(child_goal: ChildGoal):
    """Return investment suggestions for a child goal using GoalInvestmentPlanner.
    The horizon is calculated as target_year - current year.
    """
    current_year = datetime.utcnow().year
    horizon_years = max(child_goal.target_year - current_year, 0)
    planner = GoalInvestmentPlanner()
    try:
        suggestions = planner.recommend_for_horizon(horizon_years)
    except AttributeError:
        suggestions = [
            {'instrument': 'Large‑Cap Index Fund', 'allocation_pct': 40},
            {'instrument': 'Mid‑Cap Index Fund', 'allocation_pct': 20},
            {'instrument': 'International Index Fund', 'allocation_pct': 20},
            {'instrument': 'Debt Fund', 'allocation_pct': 20},
        ]
    return suggestions

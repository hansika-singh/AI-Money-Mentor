"""
tests/test_goal_planner.py
---------------------------
Unit tests for utils/sip.py — Goal-Based Savings Planner (reverse SIP).

All tests are pure-math: no network calls, no LLM, no env variables.
Run with:  pytest tests/test_goal_planner.py -v
"""

import pytest
from utils.sip import calculate_goal_sip, calculate_sip


class TestCalculateGoalSip:
    """Tests for the reverse-SIP (goal -> required monthly investment) formula."""

    def test_zero_rate_splits_goal_evenly(self):
        """At 0% annual rate, monthly SIP is simply goal / months."""
        result = calculate_goal_sip(goal=120000, rate=0, years=1)
        assert result["monthly_sip"] == 10000.0
        assert result["total_invested"] == 120000.0
        assert result["returns"] == 0.0

    def test_positive_rate_requires_less_than_zero_rate(self):
        """A positive return rate should require a smaller monthly SIP than 0%."""
        zero_rate = calculate_goal_sip(goal=1000000, rate=0, years=5)
        positive_rate = calculate_goal_sip(goal=1000000, rate=12, years=5)
        assert positive_rate["monthly_sip"] < zero_rate["monthly_sip"]

    def test_returns_dict_type(self):
        result = calculate_goal_sip(goal=500000, rate=10, years=3)
        assert isinstance(result, dict)
        assert set(result.keys()) == {"monthly_sip", "total_invested", "returns"}

    def test_total_invested_plus_returns_equals_goal(self):
        result = calculate_goal_sip(goal=1000000, rate=12, years=3)
        assert abs((result["total_invested"] + result["returns"]) - 1000000) < 0.01

    def test_round_trip_with_calculate_sip(self):
        """Feeding the resulting monthly SIP back into calculate_sip should
        reproduce (approximately) the original goal amount."""
        goal = 1000000
        rate = 12
        years = 3
        result = calculate_goal_sip(goal=goal, rate=rate, years=years)

        fv = calculate_sip(monthly=result["monthly_sip"], rate=rate, years=years)
        assert abs(fv["nominal_value"] - goal) < 1.0

    @pytest.mark.parametrize("goal,rate,years", [
        (1000000, 12, 3),
        (500000, 8, 5),
        (5000000, 15, 20),
    ])
    def test_monthly_sip_always_positive(self, goal, rate, years):
        result = calculate_goal_sip(goal, rate, years)
        assert result["monthly_sip"] > 0

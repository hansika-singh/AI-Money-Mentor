"""
tests/test_tax.py
-----------------
Unit tests for utils/tax.py — Indian income tax calculator.

Tests cover both New Regime and Old Regime slabs, the 87A rebate,
the 4% education cess, and edge cases like zero income and very
high incomes crossing the 15 lakh slab boundary.

Run with:  pytest tests/test_tax.py -v
"""

import pytest
from utils.tax import calculate_tax


class TestCalculateTax:
    """Tests for the Indian income-tax calculator."""

    # ── Helper ────────────────────────────────────────────
    @staticmethod
    def _new(income):
        return calculate_tax(income)["new_regime"]["total_tax"]

    @staticmethod
    def _old(income):
        return calculate_tax(income)["old_regime"]["total_tax"]

    # ── Zero / very low income ──────────────────────────
    def test_zero_income_no_tax(self):
        result = calculate_tax(0)
        assert result["new_regime"]["total_tax"] == 0.0
        assert result["old_regime"]["total_tax"] == 0.0

    def test_income_below_new_regime_exemption_no_tax(self):
        """New regime: income ≤ 7 lakh after standard deduction → 0 tax (87A rebate)."""
        assert self._new(700000) == 0.0

    def test_income_below_old_regime_exemption_no_tax(self):
        """Old regime: taxable income ≤ 5 lakh → 0 tax (87A rebate)."""
        assert self._old(550000) == 0.0

    # ── Cess is always applied ──────────────────────────
    def test_cess_is_4_percent_of_base_tax(self):
        """Cess should be exactly 4% of base tax for a mid-range income."""
        income = 1_200_000
        result = calculate_tax(income)
        new = result["new_regime"]
        assert round(new["cess"], 2) == round(new["base_tax"] * 0.04, 2)

    # ── Recommendation keys present ─────────────────────
    def test_response_has_required_keys(self):
        keys = {"gross_income", "new_regime", "old_regime", "recommended", "savings"}
        assert keys.issubset(calculate_tax(1_000_000).keys())

    def test_recommended_is_valid_string(self):
        rec = calculate_tax(1_000_000)["recommended"]
        assert rec in ("New Regime", "Old Regime")

    def test_savings_is_non_negative(self):
        assert calculate_tax(800_000)["savings"] >= 0

    # ── High income slab ────────────────────────────────
    def test_high_income_above_15L_charged_30_percent_slab(self):
        """Income > 15L should trigger 30% slab; tax must be > 0 in both regimes."""
        result = calculate_tax(2_000_000)
        assert result["new_regime"]["total_tax"] > 0
        assert result["old_regime"]["total_tax"] > 0

    # ── Standard deductions ─────────────────────────────
    def test_new_regime_standard_deduction_is_75k(self):
        assert calculate_tax(1_000_000)["new_regime"]["standard_deduction"] == 75000

    def test_old_regime_standard_deduction_is_50k(self):
        assert calculate_tax(1_000_000)["old_regime"]["standard_deduction"] == 50000

    # ── Parametrize ─────────────────────────────────────
    @pytest.mark.parametrize("income", [300_000, 600_000, 900_000, 1_200_000, 1_800_000])
    def test_total_tax_is_non_negative(self, income):
        result = calculate_tax(income)
        assert result["new_regime"]["total_tax"] >= 0
        assert result["old_regime"]["total_tax"] >= 0

    def test_custom_deductions_applied_old_regime(self):
        result = calculate_tax(1000000, deduction_80c=100000, deduction_80d=20000, deduction_hra=30000)
        assert result["deductions_applied"]["80c"] == 100000
        assert result["deductions_applied"]["80d"] == 20000
        assert result["deductions_applied"]["hra"] == 30000
        # Total deductions = 50k (std) + 100k + 20k + 30k = 200k
        assert result["deductions_applied"]["total"] == 200000
        # Taxable income = 1M - 200k = 800k
        assert result["old_regime"]["taxable_income"] == 800000

    # ── HRA Exemption Engine ───────────────────────────
    def test_calculate_hra_exemption_metro(self):
        from utils.tax import calculate_hra_exemption
        # Basic: 600,000, Rent: 180,000, HRA Received: 240,000, Metro: True
        # Tier 1: 240,000
        # Tier 2: 180,000 - 10% of 600,000 = 120,000
        # Tier 3: 50% of 600,000 = 300,000
        # Expected: min(240k, 120k, 300k) = 120,000
        res = calculate_hra_exemption(600000, 180000, 240000, True)
        assert res["actual_hra"] == 240000.0
        assert res["rent_minus_10_percent_basic"] == 120000.0
        assert res["salary_percentage_limit"] == 300000.0
        assert res["calculated_exemption"] == 120000.0

    def test_calculate_hra_exemption_non_metro(self):
        from utils.tax import calculate_hra_exemption
        # Basic: 600,000, Rent: 180,000, HRA Received: 240,000, Metro: False
        # Tier 3: 40% of 600,000 = 240,000
        res = calculate_hra_exemption(600000, 180000, 240000, False)
        assert res["salary_percentage_limit"] == 240000.0
        assert res["calculated_exemption"] == 120000.0

    def test_calculate_hra_exemption_rent_less_than_10_percent_basic(self):
        from utils.tax import calculate_hra_exemption
        # Basic: 600,000, Rent: 50,000, HRA Received: 100,000, Metro: True
        # Tier 2: 50,000 - 60,000 = -10,000 -> max(0, -10k) = 0
        res = calculate_hra_exemption(600000, 50000, 100000, True)
        assert res["rent_minus_10_percent_basic"] == 0.0
        assert res["calculated_exemption"] == 0.0

    def test_calculate_tax_integration_with_hra_inputs(self):
        hra_inputs = {
            "basic_salary": 600000.0,
            "rent_paid": 180000.0,
            "hra_received": 240000.0,
            "is_metro": True
        }
        result = calculate_tax(1000000, deduction_80c=100000, deduction_80d=20000, hra_inputs=hra_inputs)
        # HRA Exemption should be 120k
        assert result["deductions_applied"]["hra"] == 120000.0
        # Total deductions = 50k (std) + 100k + 20k + 120k = 290k
        assert result["deductions_applied"]["total"] == 290000.0
        assert result["hra_exemption_details"]["calculated_exemption"] == 120000.0

    def test_simulate_tax_scenarios_integration_with_hra_inputs(self):
        from utils.tax import simulate_tax_scenarios
        scenario_a = {
            "deduction_80c": 100000.0,
            "deduction_80d": 20000.0,
            "hra_inputs": {
                "basic_salary": 600000.0,
                "rent_paid": 180000.0,
                "hra_received": 240000.0,
                "is_metro": True
            }
        }
        scenario_b = {
            "deduction_80c": 150000.0,
            "deduction_80d": 25000.0,
            "hra_inputs": {
                "basic_salary": 600000.0,
                "rent_paid": 200000.0,
                "hra_received": 240000.0,
                "is_metro": True
            }
        }
        res = simulate_tax_scenarios(1200000, scenario_a, scenario_b)
        assert res["scenario_a"]["deductions_applied"]["hra"] == 120000.0
        assert res["scenario_b"]["deductions_applied"]["hra"] == 140000.0


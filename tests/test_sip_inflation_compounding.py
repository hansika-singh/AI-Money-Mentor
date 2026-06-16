"""tests/test_sip_inflation_compounding.py
----------------------------------------
Unit tests for SIP inflation adjustment compounding basis.

These tests encode the expectation that inflation adjustment should be
consistent with the compounding frequency used when projecting nominal FV.

In utils/sip.py, nominal FV is computed using monthly compounding.
Therefore, inflation discounting should also use monthly compounding.
"""

import pytest

from utils.sip import calculate_sip


def expected_inflation_adjusted_value_monthly_compounding(
    *, monthly: float, rate: float, years: float, inflation_rate: float
) -> float:
    """Replicates calculate_sip nominal FV (monthly compounding) and then
    discounts using monthly inflation compounding.
    """

    n = int(years * 12)

    if rate == 0:
        fv = monthly * n
    else:
        r = rate / 100 / 12
        fv = monthly * (((1 + r) ** n - 1) / r) * (1 + r)

    m = inflation_rate / 100 / 12
    fv_adjusted = fv / ((1 + m) ** (years * 12))

    return round(fv_adjusted, 2)


class TestSipInflationCompounding:
    def test_inflation_adjusted_value_uses_monthly_compounding(self):
        # Parameters chosen to avoid large rounding edges.
        result = calculate_sip(monthly=1000, rate=12, years=5, inflation_rate=6.0)

        expected = expected_inflation_adjusted_value_monthly_compounding(
            monthly=1000, rate=12, years=5, inflation_rate=6.0
        )
        assert result["inflation_adjusted_value"] == expected

    def test_inflation_adjusted_value_differs_from_yearly_exponent_model(self):
        # This is a regression test to catch the bug where inflation is discounted
        # using (1 + inflation) ** years while nominal FV was computed monthly.
        result = calculate_sip(monthly=1000, rate=12, years=5, inflation_rate=6.0)

        # Compute the buggy yearly-exponent model for comparison.
        # (Nominal FV computed same as calculate_sip.)
        nominal = calculate_sip(monthly=1000, rate=12, years=5)["nominal_value"]
        expected_buggy = round(nominal / (1.06 ** 5), 2)

        assert result["inflation_adjusted_value"] != expected_buggy

    @pytest.mark.parametrize("years", [0.5, 1, 2.25])
    def test_fractional_years_monthly_basis_matches_expectation(self, years):
        result = calculate_sip(monthly=2500, rate=9.5, years=years, inflation_rate=5.5)
        expected = expected_inflation_adjusted_value_monthly_compounding(
            monthly=2500, rate=9.5, years=years, inflation_rate=5.5
        )
        assert result["inflation_adjusted_value"] == expected


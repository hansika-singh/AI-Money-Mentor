def calculate_hlv(age: int, retirement_age: int, annual_income: float, personal_expenses: float, liabilities: float, savings: float) -> float:
    """
    Calculate Human Life Value (HLV) for life insurance cover.
    HLV = (Annual Income - Personal Expenses) * (Retirement Age - Age) + Liabilities - Savings
    """
    years_to_retirement = max(0, retirement_age - age)
    net_contribution = max(0.0, annual_income - personal_expenses)
    future_earnings_replacement = net_contribution * years_to_retirement
    required_cover = future_earnings_replacement + liabilities - savings
    return max(0.0, required_cover)


def recommend_health_cover(family_size: str, tier: str, pre_existing: bool) -> float:
    """
    Suggest health insurance sum insured based on family size, city tier, and pre-existing conditions.
    """
    # Base recommendation in Indian Rupees (INR)
    if family_size == "Individual":
        base_cover = 500000.0 if tier == "1" else 300000.0
    elif family_size == "Couple":
        base_cover = 700000.0 if tier == "1" else 500000.0
    elif family_size == "Family_1Kid":
        base_cover = 1000000.0 if tier == "1" else 700000.0
    elif family_size == "Family_2Kids":
        base_cover = 1500000.0 if tier == "1" else 1000000.0
    else:
        # Fallback
        base_cover = 500000.0

    # Add 30% loading/buffer for pre-existing conditions (e.g. diabetes, hypertension)
    if pre_existing:
        return base_cover * 1.3
    return base_cover

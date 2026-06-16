def calculate_goal_sip(goal, rate, years):
    """Reverse SIP: given a target corpus, work out the required monthly SIP.

    Uses the future-value-of-annuity-due formula (SIP at the start of each
    month), solved for the monthly contribution.
    """
    n = years * 12
    if rate == 0:
        monthly = goal / n
    else:
        r = rate / 100 / 12
        monthly = goal * r / (((1 + r) ** n - 1) * (1 + r))

    total_invested = monthly * n
    returns = goal - total_invested

    return {
        "monthly_sip": round(monthly, 2),
        "total_invested": round(total_invested, 2),
        "returns": round(returns, 2)
    }


def calculate_sip(monthly, rate, years, inflation_rate=0.0):
    n = years * 12
    if rate == 0:
        fv = monthly * n
    else:
        r = rate / 100 / 12
        fv = monthly * (((1 + r)**n - 1) / r) * (1 + r)
    
    if inflation_rate > 0:
        m = inflation_rate / 100 / 12
        fv_adjusted = fv / ((1 + m) ** n)
        return {
            "nominal_value": round(fv, 2),
            "inflation_adjusted_value": round(fv_adjusted, 2),
            "inflation_applied": inflation_rate
        }
        
    return {
        "nominal_value": round(fv, 2),
        "inflation_adjusted_value": round(fv, 2),
        "inflation_applied": 0.0
    }


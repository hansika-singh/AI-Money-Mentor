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


def calculate_stepup_sip(monthly, rate, years, stepup_type, stepup_value, inflation_rate=0.0):
    """Simulate a step-up SIP and compare it against a flat SIP.

    The monthly contribution increases once every 12 months by either
    a percentage or a fixed rupee amount, compounding monthly at the
    given annual rate (annuity-due convention, matching calculate_sip).
    Returns nominal totals plus a year-by-year breakdown so the
    frontend can chart step-up growth against flat growth.

    Args:
        monthly: Starting monthly SIP amount.
        rate: Expected annual return rate (%).
        years: Investment duration in years.
        stepup_type: "percentage" or "amount".
        stepup_value: Annual increase, e.g. 10 for 10%, or 1000 for Rs 1,000.
        inflation_rate: Optional annual inflation rate (%) for adjusted value.
    """
    if stepup_type not in ("percentage", "amount"):
        raise ValueError("stepup_type must be 'percentage' or 'amount'")

    n = years * 12
    r = rate / 100 / 12

    def _simulate(apply_stepup):
        current = monthly
        corpus = 0.0
        invested = 0.0
        yearly = []
        for month in range(1, n + 1):
            if apply_stepup and month > 1 and (month - 1) % 12 == 0:
                if stepup_type == "percentage":
                    current = current * (1 + stepup_value / 100)
                else:
                    current = current + stepup_value
            corpus = (corpus + current) * (1 + r)
            invested += current
            if month % 12 == 0:
                yearly.append({
                    "year": month // 12,
                    "invested": round(invested, 2),
                    "value": round(corpus, 2)
                })
        return corpus, invested, yearly

    stepup_corpus, stepup_invested, stepup_yearly = _simulate(True)
    flat_corpus, flat_invested, flat_yearly = _simulate(False)

    yearly_breakdown = [
        {
            "year": s["year"],
            "flat_value": f["value"],
            "stepup_value": s["value"],
            "flat_invested": f["invested"],
            "stepup_invested": s["invested"]
        }
        for s, f in zip(stepup_yearly, flat_yearly)
    ]

    result = {
        "stepup_nominal_value": round(stepup_corpus, 2),
        "stepup_total_invested": round(stepup_invested, 2),
        "flat_nominal_value": round(flat_corpus, 2),
        "flat_total_invested": round(flat_invested, 2),
        "yearly_breakdown": yearly_breakdown,
        "inflation_applied": 0.0
    }

    if inflation_rate > 0:
        m = inflation_rate / 100 / 12
        result["stepup_inflation_adjusted_value"] = round(stepup_corpus / ((1 + m) ** n), 2)
        result["flat_inflation_adjusted_value"] = round(flat_corpus / ((1 + m) ** n), 2)
        result["inflation_applied"] = inflation_rate
    else:
        result["stepup_inflation_adjusted_value"] = result["stepup_nominal_value"]
        result["flat_inflation_adjusted_value"] = result["flat_nominal_value"]

    return result

def calculate_tax(income, deduction_80c=0.0, deduction_80d=0.0, deduction_hra=0.0):
    # Income represents Gross Annual Income
    
    # 1. New Regime Calculation (FY 2024-25 / FY 2025-26)
    std_deduction_new = 75000
    taxable_new = max(0.0, income - std_deduction_new)
    
    tax_new = 0.0
    # Slabs:
    # 0 - 3L: 0%
    # 3L - 7L: 5%
    # 7L - 10L: 10%
    # 10L - 12L: 15%
    # 12L - 15L: 20%
    # >15L: 30%
    if taxable_new <= 300000:
        tax_new = 0.0
    elif taxable_new <= 700000:
        tax_new = (taxable_new - 300000) * 0.05
    elif taxable_new <= 1000000:
        tax_new = 400000 * 0.05 + (taxable_new - 700000) * 0.10
    elif taxable_new <= 1200000:
        tax_new = 400000 * 0.05 + 300000 * 0.10 + (taxable_new - 1000000) * 0.15
    elif taxable_new <= 1500000:
        tax_new = 400000 * 0.05 + 300000 * 0.10 + 200000 * 0.15 + (taxable_new - 1200000) * 0.20
    else:
        tax_new = 400000 * 0.05 + 300000 * 0.10 + 200000 * 0.15 + 300000 * 0.20 + (taxable_new - 1500000) * 0.30
        
    # Rebate under Sec 87A for New Regime:
    if taxable_new <= 700000:
        tax_new = 0.0
        
    cess_new = tax_new * 0.04
    total_new = round(tax_new + cess_new, 2)
    
    # 2. Old Regime Calculation with custom deductions
    # Deductions cap logic:
    # 80C capped at 1.5 Lakhs (150,000)
    # 80D capped at 25,000 (standard limit)
    ded_80c = min(150000.0, float(deduction_80c))
    ded_80d = min(25000.0, float(deduction_80d))
    ded_hra = float(deduction_hra)
    
    std_deduction_old = 50000
    total_deductions_old = std_deduction_old + ded_80c + ded_80d + ded_hra
    taxable_old = max(0.0, income - total_deductions_old)
    
    tax_old = 0.0
    # Slabs:
    # 0 - 2.5L: 0%
    # 2.5L - 5L: 5%
    # 5L - 10L: 20%
    # >10L: 30%
    if taxable_old <= 250000:
        tax_old = 0.0
    elif taxable_old <= 500000:
        tax_old = (taxable_old - 250000) * 0.05
    elif taxable_old <= 1000000:
        tax_old = 250000 * 0.05 + (taxable_old - 500000) * 0.20
    else:
        tax_old = 250000 * 0.05 + 500000 * 0.20 + (taxable_old - 1000000) * 0.30
        
    # Rebate under Sec 87A for Old Regime:
    if taxable_old <= 500000:
        tax_old = 0.0
        
    cess_old = tax_old * 0.04
    total_old = round(tax_old + cess_old, 2)
    
    return {
        "gross_income": income,
        "deductions_applied": {
            "80c": ded_80c,
            "80d": ded_80d,
            "hra": ded_hra,
            "total": total_deductions_old
        },
        "new_regime": {
            "standard_deduction": std_deduction_new,
            "taxable_income": taxable_new,
            "base_tax": round(tax_new, 2),
            "cess": round(cess_new, 2),
            "total_tax": total_new
        },
        "old_regime": {
            "standard_deduction": std_deduction_old,
            "taxable_income": taxable_old,
            "base_tax": round(tax_old, 2),
            "cess": round(cess_old, 2),
            "total_tax": total_old
        },
        "recommended": "New Regime" if total_new < total_old else "Old Regime",
        "savings": round(abs(total_old - total_new), 2)
    }


def _r2(x):
    return round(float(x), 2)


def _tax_total_for_regime(calc_result, regime_key):
    return float(calc_result[regime_key]["total_tax"])


def _sensitivity_by_rupee(income, deduction_80c=0.0, deduction_80d=0.0, deduction_hra=0.0):
    """
    Returns marginal tax deltas per ₹1 change in each deduction, computed via
    finite difference: tax(d+1) - tax(d). Caps in calculate_tax naturally apply.
    """
    base = calculate_tax(income, deduction_80c=deduction_80c, deduction_80d=deduction_80d, deduction_hra=deduction_hra)

    deltas = {
        "new_regime": {"80c_delta_per_1": 0.0, "80d_delta_per_1": 0.0, "hra_delta_per_1": 0.0},
        "old_regime": {"80c_delta_per_1": 0.0, "80d_delta_per_1": 0.0, "hra_delta_per_1": 0.0},
    }

    # 80C (+1)
    plus_80c = calculate_tax(income, deduction_80c=deduction_80c + 1, deduction_80d=deduction_80d, deduction_hra=deduction_hra)
    deltas["new_regime"]["80c_delta_per_1"] = _r2(_tax_total_for_regime(plus_80c, "new_regime") - _tax_total_for_regime(base, "new_regime"))
    deltas["old_regime"]["80c_delta_per_1"] = _r2(_tax_total_for_regime(plus_80c, "old_regime") - _tax_total_for_regime(base, "old_regime"))

    # 80D (+1)
    plus_80d = calculate_tax(income, deduction_80c=deduction_80c, deduction_80d=deduction_80d + 1, deduction_hra=deduction_hra)
    deltas["new_regime"]["80d_delta_per_1"] = _r2(_tax_total_for_regime(plus_80d, "new_regime") - _tax_total_for_regime(base, "new_regime"))
    deltas["old_regime"]["80d_delta_per_1"] = _r2(_tax_total_for_regime(plus_80d, "old_regime") - _tax_total_for_regime(base, "old_regime"))

    # HRA (+1)
    plus_hra = calculate_tax(income, deduction_80c=deduction_80c, deduction_80d=deduction_80d, deduction_hra=deduction_hra + 1)
    deltas["new_regime"]["hra_delta_per_1"] = _r2(_tax_total_for_regime(plus_hra, "new_regime") - _tax_total_for_regime(base, "new_regime"))
    deltas["old_regime"]["hra_delta_per_1"] = _r2(_tax_total_for_regime(plus_hra, "old_regime") - _tax_total_for_regime(base, "old_regime"))

    return deltas


def simulate_tax_scenarios(
    income,
    scenario_a,
    scenario_b,
):
    """
    scenario_a / scenario_b are dicts with:
      - deduction_80c
      - deduction_80d
      - deduction_hra

    Returns deterministic output:
      - scenario_a: full calculate_tax output
      - scenario_b: full calculate_tax output
      - scenario switch deltas (A -> B): total tax deltas per regime
      - sensitivity deltas per ₹1 change in each deduction for each scenario+regime
      - deterministic lever ranking for offline explanation
    """
    def _pick(sc):
        return {
            "deduction_80c": float(sc.get("deduction_80c", 0.0)),
            "deduction_80d": float(sc.get("deduction_80d", 0.0)),
            "deduction_hra": float(sc.get("deduction_hra", 0.0)),
        }

    a_in = _pick(scenario_a)
    b_in = _pick(scenario_b)

    a_calc = calculate_tax(
        income,
        deduction_80c=a_in["deduction_80c"],
        deduction_80d=a_in["deduction_80d"],
        deduction_hra=a_in["deduction_hra"],
    )
    b_calc = calculate_tax(
        income,
        deduction_80c=b_in["deduction_80c"],
        deduction_80d=b_in["deduction_80d"],
        deduction_hra=b_in["deduction_hra"],
    )

    # Switching A -> B deltas (B - A)
    delta_new_total = _r2(b_calc["new_regime"]["total_tax"] - a_calc["new_regime"]["total_tax"])
    delta_old_total = _r2(b_calc["old_regime"]["total_tax"] - a_calc["old_regime"]["total_tax"])

    # "Savings under new regime" when switching A -> B
    # If delta is negative, B saves; we report positive savings amount.
    new_savings_switch = _r2(max(0.0, -delta_new_total))
    old_savings_switch = _r2(max(0.0, -delta_old_total))

    # Sensitivity (per ₹1 change) for each scenario
    a_sens = _sensitivity_by_rupee(
        income,
        deduction_80c=a_in["deduction_80c"],
        deduction_80d=a_in["deduction_80d"],
        deduction_hra=a_in["deduction_hra"],
    )
    b_sens = _sensitivity_by_rupee(
        income,
        deduction_80c=b_in["deduction_80c"],
        deduction_80d=b_in["deduction_80d"],
        deduction_hra=b_in["deduction_hra"],
    )

    def _rank_levers(sens_for_regime):
        # Most negative delta per ₹1 reduces tax (best). If all >=0, still return largest deltas first.
        candidates = [
            ("80C", sens_for_regime["80c_delta_per_1"]),
            ("80D", sens_for_regime["80d_delta_per_1"]),
            ("HRA", sens_for_regime["hra_delta_per_1"]),
        ]
        candidates_sorted = sorted(candidates, key=lambda x: x[1])  # ascending (more negative first)
        return [
            {
                "lever": name,
                "delta_per_1": float(delta),
            }
            for name, delta in candidates_sorted
        ]

    best_regime_a = a_calc["recommended"]
    best_regime_b = b_calc["recommended"]

    # For deterministic offline explanation, choose lever ranking for each scenario's recommended regime.
    sens_a_for_best = a_sens["new_regime"] if best_regime_a == "New Regime" else a_sens["old_regime"]
    sens_b_for_best = b_sens["new_regime"] if best_regime_b == "New Regime" else b_sens["old_regime"]

    comparison = {
        "switch": {
            "new_regime": {"delta_total_tax": delta_new_total, "savings": new_savings_switch},
            "old_regime": {"delta_total_tax": delta_old_total, "savings": old_savings_switch},
        },
        "best_scenario_by_savings_under_recommended_regime": (
            "A" if (a_calc["savings"] >= b_calc["savings"]) else "B"
        ),
        "best_regime": {
            "scenario_a": best_regime_a,
            "scenario_b": best_regime_b,
        },
    }

    return {
        "income": float(income),
        "scenario_a": a_calc,
        "scenario_b": b_calc,
        "comparison": comparison,
        "sensitivity": {
            "scenario_a": {
                "new_regime": a_sens["new_regime"],
                "old_regime": a_sens["old_regime"],
                "lever_ranking_for_best_regime": _rank_levers(sens_a_for_best),
            },
            "scenario_b": {
                "new_regime": b_sens["new_regime"],
                "old_regime": b_sens["old_regime"],
                "lever_ranking_for_best_regime": _rank_levers(sens_b_for_best),
            },
        },
    }


from flask import Flask, request, jsonify, render_template
import yfinance as yf
import os
import sys
from groq import Groq
from dotenv import load_dotenv

# Load environment variables from .env file (if present)
load_dotenv()

# Log a warning to console if API key is missing, enabling offline mode.
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY or GROQ_API_KEY.strip() in ("", "your_groq_api_key_here"):
    print(
        "\n[WARNING] GROQ_API_KEY is not configured. AI features will run in offline mode.\n"
        "  1. Copy .env.example to .env\n"
        "  2. Set your GROQ_API_KEY in .env\n"
        "  Obtain a free key at: https://console.groq.com/\n",
        file=sys.stderr,
    )
    client = None
else:
    client = Groq(api_key=GROQ_API_KEY)
# ---------------- IMPORT UTILS ----------------
from utils.sip import calculate_sip, calculate_goal_sip
from utils.tax import calculate_tax
from utils.pdf_parser import extract_income
from utils.money_score import calculate_money_score
from utils.multi_agent import run_multi_agent
from utils.stock import get_stock_price
from utils.expense_track import calculate_expense, insights
from utils.validation import ValidationError, validate_string, validate_float, validate_int, validate_history

app = Flask(__name__)

# ---------------- INIT DATABASE ----------------
from models import (
    db,
    Expense,
    Asset,
    Liability,
    BudgetLimit,
    BudgetAlert,
    PriceAlert,
    FinancialGoal,
    FinancialGoalMilestone,
)



app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///money_mentor.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

with app.app_context():
    db.create_all()

# ---------------- INIT GROQ ----------------
# client is initialized in the startup validation block above

# ── Dev-mode startup message ─────────────────────────────────
if os.getenv("FLASK_ENV", "development") != "production":
    if client:
        print("[OK] Groq client initialised successfully.")
    else:
        print("[WARNING] Groq client is running in offline mode.")
@app.route("/")
def home():
    return render_template("dashboard.html", active_page="dashboard")

@app.route("/stock", methods=["GET"])
def stock():
    return render_template("stock.html", active_page="stock")

@app.route("/pdf-parser", methods=["GET"])
def pdf_parser():
    return render_template("pdf.html", active_page="pdf")

@app.route("/agent-page", methods=["GET"])
def agent_page():
    return render_template("agent.html", active_page="agent")

@app.route("/expense", methods=["GET"])
def expense():
    return render_template("expense.html", active_page="expense")

@app.route("/networth", methods=["GET"])
def networth():
    return render_template("networth.html", active_page="networth")

@app.route("/budget", methods=["GET"])
def budget():
    return render_template("budget.html", active_page="budget")


# ---------------- HEALTH CHECK ----------------
@app.route("/health", methods=["GET"])
def health_check():
    """Lightweight liveness probe for deployment environments (Docker, Railway, etc.)."""
    return jsonify({"status": "ok", "service": "AI Money Mentor"}), 200


# ---------------- AI STATUS (Issue #218) ----------------
@app.route("/api/status", methods=["GET"])
def ai_status():
    """
    Reports whether the Groq AI client is available.
    The frontend can call this on page load to show/hide AI-dependent UI
    and display an informative offline banner instead of a confusing error.
    """
    if client is not None:
        return jsonify({
            "ai_online": True,
            "message": "AI Money Mentor is online and ready."
        })
    return jsonify({
        "ai_online": False,
        "message": (
            "AI features are unavailable — GROQ_API_KEY is not configured. "
            "Set GROQ_API_KEY in your .env file to enable AI features."
        )
    })


# ---------------- ERROR HANDLERS ----------------
@app.errorhandler(ValidationError)
def handle_validation_error(error):
    return jsonify({
        "error": "Bad Request",
        "message": str(error),
        "status_code": 400
    }), 400

@app.errorhandler(400)
def bad_request(error):
    return jsonify({
        "error": "Bad Request",
        "message": str(error),
        "status_code": 400
    }), 400


@app.errorhandler(404)
def not_found(error):
    # Return HTML page for browser navigation, JSON for API clients
    if request.accept_mimetypes.accept_html and not request.accept_mimetypes.accept_json:
        return render_template("404.html", active_page=None), 404
    return jsonify({
        "error": "Not Found",
        "message": "The requested endpoint does not exist.",
        "status_code": 404
    }), 404


@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        "error": "Method Not Allowed",
        "message": str(error),
        "status_code": 405
    }), 405


@app.errorhandler(500)
def internal_server_error(error):
    return jsonify({
        "error": "Internal Server Error",
        "message": "An unexpected error occurred. Please try again later.",
        "status_code": 500
    }), 500


# ---------------- 🤖 AI CHAT ----------------
@app.route("/chat", methods=["GET", "POST"])
def chat():
    if request.method == "GET":
        return render_template("chat.html", active_page="chat")
    try:
        if client is None:
            return jsonify({
                "reply": "AI Money Mentor is offline because GROQ_API_KEY is not configured. Please set GROQ_API_KEY in your env/config files."
            })

        data = request.json or {}
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object")
        msg = validate_string(data.get("message"), "message")
        history = validate_history(data.get("history"))

        # Build messages: system prompt + last 10 history turns + current message
        system_prompt = (
            "You are an expert AI financial advisor for Indian users.\n\n"
            "Your job:\n"
            "- Help users manage money smartly\n"
            "- Teach budgeting, saving, and investing\n"
            "- Give simple, practical, real-life advice\n\n"
            "Response rules:\n"
            "- Always use structured format:\n"
            "Income / Situation Summary:\n"
            "- ...\n"
            "Budget Breakdown (if applicable):\n"
            "- Needs: 50%\n"
            "- Wants: 30%\n"
            "- Savings: 20%\n"
            "Advice:\n"
            "- Give clear steps\n"
            "- Keep it simple and actionable\n\n"
            "Tone:\n"
            "- Friendly, practical, and easy to understand"
        )
        messages = [{"role": "system", "content": system_prompt}]
        messages += history[-10:]
        messages.append({"role": "user", "content": msg})

        res = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages
        )
        return jsonify({
            "reply": res.choices[0].message.content
        })

    except ValidationError as e:
        raise e
    except Exception as e:
        app.logger.error(f"Groq API Error: {str(e)}")
        return jsonify({
            "reply": "Unable to generate a response at the moment. Please try again later."
        }), 500


# ---------------- 💸 SIP ----------------
@app.route("/sip", methods=["GET", "POST"])
def sip():
    if request.method == "GET":
        return render_template("sip.html", active_page="sip")
    try:
        data = request.json or {}
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object")
        monthly = validate_float(data.get("monthly"), "monthly", min_val=0.0)
        rate = validate_float(data.get("rate"), "rate", min_val=0.0)
        years = validate_int(data.get("years"), "years", min_val=1)
        inflation = validate_float(data.get("inflation", 0.0), "inflation", min_val=0.0)

        result = calculate_sip(monthly, rate, years, inflation)
        return jsonify({
            "future_value": result["nominal_value"],
            "nominal_value": result["nominal_value"],
            "inflation_adjusted_value": result["inflation_adjusted_value"],
            "inflation_applied": result["inflation_applied"]
        })

    except ValidationError as e:
        raise e
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ---------------- 🎯 GOAL-BASED SAVINGS PLANNER ----------------
@app.route("/goal-planner", methods=["GET", "POST"])
def goal_planner():
    if request.method == "GET":
        return render_template("goal_planner.html", active_page="goal_planner")
    try:
        data = request.json or {}
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object")
        goal = validate_float(data.get("goal"), "goal", min_val=0.01)
        rate = validate_float(data.get("rate"), "rate", min_val=0.0)
        years = validate_int(data.get("years"), "years", min_val=1)

        result = calculate_goal_sip(goal, rate, years)
        return jsonify(result)

    except ValidationError as e:
        raise e
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ---------------- 📊 STOCK ----------------
@app.route("/portfolio", methods=["POST"])
def portfolio():
    try:
        data = request.json or {}
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object")
        stock = validate_string(data.get("stock"), "stock").upper()
        result = get_stock_price(stock)
        if "error" in result:
            raise ValidationError(result["error"])
        return jsonify(result)

    except ValidationError as e:
        raise e
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/alerts", methods=["GET"])
def get_alerts():
    try:
        alerts = PriceAlert.query.all()
        return jsonify([a.to_dict() for a in alerts])
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/alerts", methods=["POST"])
def create_alert():
    try:
        data = request.json
        if not data or "symbol" not in data or "target_price" not in data:
            return jsonify({"error": "Missing required fields"}), 400
        
        symbol = data["symbol"].strip().upper()
        target_price = float(data["target_price"])
        condition = data.get("condition", "above").strip().lower()
        
        if condition not in ("above", "below"):
            return jsonify({"error": "Invalid condition value"}), 400
            
        alert = PriceAlert(symbol=symbol, target_price=target_price, condition=condition)
        db.session.add(alert)
        db.session.commit()
        return jsonify(alert.to_dict()), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/alerts/<int:alert_id>", methods=["DELETE"])
def delete_alert(alert_id):
    try:
        alert = PriceAlert.query.get(alert_id)
        if not alert:
            return jsonify({"error": "Alert not found"}), 404
        db.session.delete(alert)
        db.session.commit()
        return jsonify({"status": "success", "message": "Alert deleted successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    
# ---------------- 💸 TAX ----------------
@app.route("/tax", methods=["GET", "POST"])
def tax():
    if request.method == "GET":
        return render_template("tax.html", active_page="tax")
    try:
        data = request.json or {}
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object")
        income = validate_float(data.get("income"), "income", min_val=0.0)
        deduction_80c = validate_float(data.get("deduction_80c", 0.0), "deduction_80c", min_val=0.0)
        deduction_80d = validate_float(data.get("deduction_80d", 0.0), "deduction_80d", min_val=0.0)
        deduction_hra = validate_float(data.get("deduction_hra", 0.0), "deduction_hra", min_val=0.0)
        
        tax_details = calculate_tax(
            income,
            deduction_80c=deduction_80c,
            deduction_80d=deduction_80d,
            deduction_hra=deduction_hra
        )
        
        # AI Tax-saving advice
        recommendations = "You are already in the zero-tax bracket! No additional tax-saving investments are required."
        
        recommended_regime = tax_details.get("recommended", "New Regime")
        regime_key = "new_regime" if recommended_regime == "New Regime" else "old_regime"
        total_tax = tax_details.get(regime_key, {}).get("total_tax", 0.0)
        
        # Only query AI if there is actual tax payable and client is available
        if total_tax > 0.0 and client:
            prompt = (
                f"A user in India has a gross annual income of ₹{income:,} and has a total tax liability of "
                f"₹{total_tax:,} under the recommended {recommended_regime}.\n\n"
                f"Generate a customized list of tax-saving investment recommendations for them. "
                f"Suggest specific options under Section 80C (up to 1.5L, e.g. ELSS, PPF), Section 80CCD(1B) (up to 50k in NPS), "
                f"and Section 80D (Health Insurance). Be brief and format the response as a bulleted list with clear estimated tax savings."
            )
            
            try:
                ai_res = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": "You are a professional Indian tax consultant. Give brief, actionable advice."},
                        {"role": "user", "content": prompt}
                    ]
                )
                recommendations = ai_res.choices[0].message.content.strip()
            except Exception as ai_err:
                app.logger.error(f"Tax AI Recommendation Error: {str(ai_err)}")
                recommendations = "AI Tax recommendations are currently unavailable. Consider investing in ELSS or NPS to reduce your tax."
        elif total_tax > 0.0:
            recommendations = "AI Tax recommendations are currently offline (no GROQ_API_KEY configured). Consider investing in ELSS or NPS to reduce your tax."
                
        tax_details["ai_recommendations"] = recommendations
        return jsonify({"tax": tax_details})

    except ValidationError as e:
        raise e
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/tax/simulate", methods=["POST"])
def tax_simulate():
    try:
        from utils.tax import simulate_tax_scenarios

        data = request.json or {}
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object")

        income = validate_float(data.get("income"), "income", min_val=0.0)

        scenario_a = data.get("scenario_a") or {}
        scenario_b = data.get("scenario_b") or {}

        if not isinstance(scenario_a, dict) or not isinstance(scenario_b, dict):
            raise ValidationError("'scenario_a' and 'scenario_b' must be objects")

        scenario_a_d80c = validate_float(scenario_a.get("deduction_80c", 0.0), "scenario_a.deduction_80c", min_val=0.0)
        scenario_a_d80d = validate_float(scenario_a.get("deduction_80d", 0.0), "scenario_a.deduction_80d", min_val=0.0)
        scenario_a_hra = validate_float(scenario_a.get("deduction_hra", 0.0), "scenario_a.deduction_hra", min_val=0.0)

        scenario_b_d80c = validate_float(scenario_b.get("deduction_80c", 0.0), "scenario_b.deduction_80c", min_val=0.0)
        scenario_b_d80d = validate_float(scenario_b.get("deduction_80d", 0.0), "scenario_b.deduction_80d", min_val=0.0)
        scenario_b_hra = validate_float(scenario_b.get("deduction_hra", 0.0), "scenario_b.deduction_hra", min_val=0.0)

        result = simulate_tax_scenarios(
            income,
            scenario_a={
                "deduction_80c": scenario_a_d80c,
                "deduction_80d": scenario_a_d80d,
                "deduction_hra": scenario_a_hra,
            },
            scenario_b={
                "deduction_80c": scenario_b_d80c,
                "deduction_80d": scenario_b_d80d,
                "deduction_hra": scenario_b_hra,
            },
        )

        # Deterministic explanation always available
        best_regime_a = result["best_regime"]["scenario_a"]
        best_regime_b = result["best_regime"]["scenario_b"]
        switch_savings_new = float(result["comparison"]["switch"]["new_regime"]["savings"])
        switch_savings_old = float(result["comparison"]["switch"]["old_regime"]["savings"])

        # pick regime under which switching A->B saves more (deterministic)
        if switch_savings_new >= switch_savings_old and switch_savings_new > 0:
            regime_for_explanation = "New Regime"
        elif switch_savings_old > 0:
            regime_for_explanation = "Old Regime"
        else:
            regime_for_explanation = result["comparison"]["best_scenario_by_savings_under_recommended_regime"]

        # Build deterministic lever explanation from sensitivity rankings for the best regime of scenario B
        scenario_b_best = best_regime_b
        sens_for_scenario_b = result["sensitivity"]["scenario_b"]["new_regime"] if scenario_b_best == "New Regime" else result["sensitivity"]["scenario_b"]["old_regime"]
        lever_ranking = result["sensitivity"]["scenario_b"]["new_regime"]["lever_ranking_for_best_regime"] if scenario_b_best == "New Regime" else result["sensitivity"]["scenario_b"]["old_regime"]["lever_ranking_for_best_regime"]

        deterministic_explanation = (
            f"Regime outcome: Scenario A is better under {best_regime_a}, while Scenario B is better under {best_regime_b}. "
            f"Under {scenario_b_best}, the biggest tax lever tends to be: {lever_ranking[0]['lever']} "
            f"(≈ {abs(lever_ranking[0]['delta_per_1']):.2f} tax change per ₹1). "
        )

        if client:
            # AI explanation prompt (use computed deltas + savings)
            prompt = (
                f"User wants to compare tax scenarios in India.\n\n"
                f"Income: ₹{result['income']:.0f}\n\n"
                f"Scenario A recommended regime: {best_regime_a}\n"
                f"Scenario B recommended regime: {best_regime_b}\n\n"
                f"Switching A -> B savings:\n"
                f"- New regime savings: ₹{switch_savings_new:.2f}\n"
                f"- Old regime savings: ₹{switch_savings_old:.2f}\n\n"
                f"Sensitivity (Scenario B, per ₹1 increase):\n"
                f"{lever_ranking}\n\n"
                f"Explain in simple terms why the winning regime is likely to be {best_regime_b} "
                f"and which levers (80C/80D/HRA) give the biggest savings. "
                f"Use bullet points and keep it under 8 lines."
            )
            try:
                ai_res = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": "You are a professional Indian tax consultant. Provide concise, actionable insights."},
                        {"role": "user", "content": prompt},
                    ],
                )
                explanation = ai_res.choices[0].message.content.strip()
            except Exception as ai_err:
                app.logger.error(f"Tax simulate AI error: {str(ai_err)}")
                explanation = deterministic_explanation
        else:
            explanation = deterministic_explanation

        result["explanation"] = explanation
        result["ai_available"] = client is not None

        return jsonify({"result": result})

    except ValidationError as e:
        raise e
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ---------------- 📄 PDF ----------------
@app.route("/upload", methods=["POST"])
def upload():
    try:
        file = request.files["file"]
        result = extract_income(file)
        return jsonify({"data": result})

    except Exception as e:
        return jsonify({"error": str(e)})


# ---------------- 🧠 MULTI AGENT ----------------
@app.route("/agent", methods=["POST"])
def run_agent_route():
    if not client:
        return jsonify({
            "error": "AI Agent is offline: GROQ_API_KEY is not configured on the server."
        })
    try:
        if client is None:
            return jsonify({
                "error": "AI Multi-Agent is offline because GROQ_API_KEY is not configured. Please set GROQ_API_KEY in your env/config files."
            })
        data = request.json or {}
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object")
        query = validate_string(data.get("query"), "query")
        response = run_multi_agent(client, query)
        return jsonify({"response": response})

    except ValidationError as e:
        raise e
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ---------------- 💰 MONEY SCORE ----------------
@app.route("/money-score", methods=["GET", "POST"])
def money_score():
    if request.method == "GET":
        return render_template("score.html", active_page="score")
    try:
        data = request.json or {}
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object")
        
        income = validate_float(data.get("income"), "income", min_val=0.0)
        expenses = validate_float(data.get("expenses"), "expenses", min_val=0.0)
        savings = validate_float(data.get("savings"), "savings", min_val=0.0)
        investments = validate_float(data.get("investments"), "investments", min_val=0.0)
        debt = validate_float(data.get("debt"), "debt", min_val=0.0)
        emergency = validate_float(data.get("emergency"), "emergency", min_val=0.0)

        score = calculate_money_score(income, expenses, savings, investments, debt, emergency)

        if score >= 80:
            status = "Excellent 💚"
        elif score >= 60:
            status = "Good 👍"
        elif score >= 40:
            status = "Average ⚠️"
        else:
            status = "Needs Improvement ❌"

        return jsonify({
            "score": score,
            "status": status
        })

    except ValidationError as e:
        raise e
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# Expense Tracker Features

@app.route("/add_expense", methods=["POST"])
def add_expense():
    try:
        data = request.json or {}
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object")
        category = validate_string(data.get("category"), "category")
        amount = validate_float(data.get("amount"), "amount", min_val=0.01)
        date = validate_string(data.get("date"), "date")

        expense = Expense(
            category=category,
            amount=amount,
            date=date
        )
        db.session.add(expense)
        db.session.commit()
        
        # Check thresholds
        ym = expense.date[:7] if len(expense.date) >= 7 else None
        run_threshold_checks(expense.category, ym)
        
        return jsonify({"status": "success"})

    except ValidationError as e:
        raise e
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/calculate", methods=["GET"])
def calculate():
    expense_data = [e.to_dict() for e in Expense.query.order_by(Expense.id).all()]
    result = calculate_expense(expense_data)
    result["expenses"] = expense_data
    return jsonify(result)

@app.route("/insights", methods=["GET"])
def expense_insights():
    expense_data = [e.to_dict() for e in Expense.query.order_by(Expense.id).all()]
    if not client:
        # Calculate standard expenses metrics but return fallback AI insights content
        totals = calculate_expense(expense_data)
        return jsonify({
            "insights": "<div class=\"insight-card\"><h3>AI Insights Offline</h3><p>Personalized AI savings suggestions are currently offline because the GROQ_API_KEY is not configured on the server. Please configure it to enable insights.</p></div>",
            "summary": totals
        })
    result = insights(client, expense_data)
    return jsonify(result)

# ---------------- NET WORTH TRACKER ----------------
# Net Worth Tracker Features

@app.route("/net-worth", methods=["GET", "POST"])
def get_net_worth():
    assets = Asset.query.order_by(Asset.id).all()
    liabilities = Liability.query.order_by(Liability.id).all()
    assets_data = [a.to_dict(i) for i, a in enumerate(assets)]
    liabilities_data = [l.to_dict(i) for i, l in enumerate(liabilities)]
    total_assets = sum(item['amount'] for item in assets_data)
    total_liabilities = sum(item['amount'] for item in liabilities_data)
    return jsonify({
        "assets": assets_data,
        "liabilities": liabilities_data,
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "net_worth": total_assets - total_liabilities
    })

@app.route("/add-asset", methods=["POST"])
def add_asset():
    try:
        data = request.json or {}
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object")
        name = validate_string(data.get("name"), "name")
        amount = validate_float(data.get("amount"), "amount", min_val=0.0)
        
        asset = Asset(name=name, amount=amount)
        db.session.add(asset)
        db.session.commit()
        return jsonify({"status": "success"})
    except ValidationError as e:
        raise e
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/add-liability", methods=["POST"])
def add_liability():
    try:
        data = request.json or {}
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object")
        name = validate_string(data.get("name"), "name")
        amount = validate_float(data.get("amount"), "amount", min_val=0.0)
        
        liability = Liability(name=name, amount=amount)
        db.session.add(liability)
        db.session.commit()
        return jsonify({"status": "success"})
    except ValidationError as e:
        raise e
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/delete-item", methods=["POST"])
def delete_item():
    try:
        data = request.json or {}
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object")
        item_type = validate_string(data.get("type"), "type")
        if item_type not in ('asset', 'liability'):
            raise ValidationError("'type' must be either 'asset' or 'liability'")
        item_db_id = validate_int(data.get("id"), "id", min_val=1)

        if item_type == "asset":
            item = Asset.query.get(item_db_id)
        else:
            item = Liability.query.get(item_db_id)

        if not item:
            return jsonify({"error": f"Item not found (type={item_type}, id={item_db_id})"}), 404

        db.session.delete(item)
        db.session.commit()
        return jsonify({"status": "success"})
    except ValidationError as e:
        raise e
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Helper to check budget thresholds
def run_threshold_checks(category, year_month=None):
    if not year_month:
        import datetime
        year_month = datetime.datetime.now().strftime("%Y-%m")
        
    limit = BudgetLimit.query.filter_by(category=category).first()
    if not limit or limit.limit_amount <= 0:
        return []
        
    expenses = Expense.query.filter(
        Expense.category == category,
        Expense.date.like(f"{year_month}%")
    ).all()
    
    total_spent = sum(e.amount for e in expenses)
    pct = total_spent / limit.limit_amount
    
    triggered = []
    for threshold in [100, 90, 80]:
        target = threshold / 100.0
        if pct >= target:
            exists = BudgetAlert.query.filter_by(
                category=category,
                year_month=year_month,
                threshold=threshold
            ).first()
            if not exists:
                alert = BudgetAlert(
                    category=category,
                    year_month=year_month,
                    threshold=threshold
                )
                db.session.add(alert)
                triggered.append(threshold)
                print(
                    f"\n[EMAIL ALERT] To: user@example.com\n"
                    f"Subject: Budget Alert: {category} spending reached {threshold}%\n"
                    f"Body: You have spent ₹{total_spent:.2f} of your ₹{limit.limit_amount:.2f} limit in category '{category}'.\n",
                    file=sys.stderr
                )
    if triggered:
        db.session.commit()
    return triggered


# ---------------- SMART BUDGET ALERTS ----------------

@app.route("/budget/limits", methods=["GET", "POST"])
def budget_limits():
    if request.method == "POST":
        try:
            data = request.json or {}
            if not isinstance(data, dict):
                raise ValidationError("Request body must be a JSON object")
            category = validate_string(data.get("category"), "category")
            limit_amount = validate_float(data.get("limit_amount"), "limit_amount", min_val=0.0)
            
            limit = BudgetLimit.query.filter_by(category=category).first()
            if limit:
                limit.limit_amount = limit_amount
            else:
                limit = BudgetLimit(category=category, limit_amount=limit_amount)
                db.session.add(limit)
            db.session.commit()
            return jsonify({"status": "success"})
        except ValidationError as e:
            raise e
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    else:
        limits = BudgetLimit.query.order_by(BudgetLimit.category).all()
        return jsonify([l.to_dict() for l in limits])

@app.route("/budget/status", methods=["GET"])
def budget_status():
    import datetime
    year_month = request.args.get("month", datetime.datetime.now().strftime("%Y-%m"))
    
    limits = BudgetLimit.query.all()
    limits_dict = {l.category: l.limit_amount for l in limits}
    
    expenses = Expense.query.filter(Expense.date.like(f"{year_month}%")).all()
    
    spent_by_category = {}
    for e in expenses:
        spent_by_category[e.category] = spent_by_category.get(e.category, 0.0) + e.amount
        
    status_list = []
    all_categories = set(limits_dict.keys()) | set(spent_by_category.keys())
    
    for cat in sorted(all_categories):
        lim = limits_dict.get(cat, 0.0)
        spent = spent_by_category.get(cat, 0.0)
        pct = (spent / lim * 100) if lim > 0 else 0.0
        status_list.append({
            "category": cat,
            "limit_amount": lim,
            "spent": spent,
            "percentage": round(pct, 2)
        })
        
    return jsonify({
        "month": year_month,
        "categories": status_list,
        "total_budgeted": sum(limits_dict.values()),
        "total_spent": sum(spent_by_category.values())
    })

@app.route("/budget/alerts", methods=["GET"])
def budget_alerts():
    alerts = BudgetAlert.query.order_by(BudgetAlert.triggered_at.desc()).limit(10).all()
    return jsonify([a.to_dict() for a in alerts])


# Delete a budget limit by ID (Issue #179)
@app.route("/budget/limits/<int:limit_id>", methods=["DELETE"])
def delete_budget_limit(limit_id):
    """Remove a category budget limit and its associated alerts."""
    try:
        limit = db.session.get(BudgetLimit, limit_id)
        if not limit:
            return jsonify({"error": f"Budget limit with id {limit_id} not found."}), 404
        # Remove any alerts tied to this category before deleting the limit
        BudgetAlert.query.filter_by(category=limit.category).delete(synchronize_session="fetch")
        db.session.delete(limit)
        db.session.commit()
        return jsonify({"status": "success", "deleted_category": limit.category})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ---------------- FINANCIAL GOALS TRACKER ----------------
def _months_diff(start_dt, end_dt):
    return (end_dt.year - start_dt.year) * 12 + (end_dt.month - start_dt.month)


def _ym_add_months(base_dt, months):
    # base_dt is a datetime; normalize to first day
    year = base_dt.year + (base_dt.month - 1 + months) // 12
    month = (base_dt.month - 1 + months) % 12 + 1
    return year, month


def compute_monthly_milestones(goal):
    """Compute milestones as an even split across months until goal.target_date.

    Returns list of dicts: [{month, target_amount_for_month, status}]
    """
    from datetime import datetime

    remaining = float(goal.target_amount) - float(goal.current_amount)
    # If already reached/exceeded, all milestones become 0 and marked completed.
    if remaining <= 0:
        target_dt = datetime.strptime(goal.target_date, "%Y-%m")
        now = datetime.now()
        months_remaining = _months_diff(datetime(now.year, now.month, 1), datetime(target_dt.year, target_dt.month, 1))
        if months_remaining < 0:
            months_remaining = 0
        if months_remaining == 0:
            months_remaining = 1

        milestones = []
        for i in range(months_remaining):
            y, m = _ym_add_months(datetime(now.year, now.month, 1), i)
            milestones.append({
                "month": f"{y:04d}-{m:02d}",
                "target_amount_for_month": 0.0,
                "status": "completed",
            })
        return milestones

    target_dt = datetime.strptime(goal.target_date, "%Y-%m")
    now = datetime.now()

    start = datetime(now.year, now.month, 1)
    end = datetime(target_dt.year, target_dt.month, 1)
    months_remaining = _months_diff(start, end)
    if months_remaining <= 0:
        months_remaining = 1

    # Even split with rounding correction on the last month.
    base = remaining / months_remaining
    amounts = [round(base, 2) for _ in range(months_remaining)]
    total_alloc = round(sum(amounts), 2)
    diff = round(remaining - total_alloc, 2)
    amounts[-1] = round(amounts[-1] + diff, 2)

    milestones = []
    for i in range(months_remaining):
        y, m = _ym_add_months(start, i)
        milestones.append({
            "month": f"{y:04d}-{m:02d}",
            "target_amount_for_month": float(amounts[i]),
            "status": "planned",
        })

    return milestones


def persist_goal_milestones(goal, milestones):
    FinancialGoalMilestone.query.filter_by(goal_id=goal.id).delete(synchronize_session=False)
    for ms in milestones:
        db.session.add(FinancialGoalMilestone(
            goal_id=goal.id,
            month=ms["month"],
            target_amount_for_month=ms["target_amount_for_month"],
            status=ms["status"],
        ))
    db.session.commit()


@app.route("/goals", methods=["GET", "POST"])
def goals():
    if request.method == "GET":
        return render_template("goals.html", active_page="goals")
    try:
        data = request.json or {}
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object")
        name = validate_string(data.get("name"), "name")
        target_amount = validate_float(data.get("target_amount"), "target_amount", min_val=0.01)
        current_amount = validate_float(data.get("current_amount", 0.0), "current_amount", min_val=0.0)
        target_date = validate_string(data.get("target_date"), "target_date")

        goal = FinancialGoal(
            name=name,
            target_amount=target_amount,
            current_amount=current_amount,
            target_date=target_date
        )
        db.session.add(goal)
        db.session.commit()

        milestones = compute_monthly_milestones(goal)
        persist_goal_milestones(goal, milestones)

        return jsonify({"status": "success", "goal": goal.to_dict()})
    except ValidationError as e:
        raise e
    except Exception as e:
        return jsonify({"error": str(e)}), 400



@app.route("/goals/<int:goal_id>", methods=["PUT", "DELETE"])
def goal_detail(goal_id):
    try:
        goal = FinancialGoal.query.get(goal_id)
        if not goal:
            return jsonify({"error": "Goal not found"}), 404

        if request.method == "DELETE":
            # Delete milestones first
            FinancialGoalMilestone.query.filter_by(goal_id=goal.id).delete(synchronize_session=False)
            db.session.delete(goal)
            db.session.commit()
            return jsonify({"status": "success"})
        else:  # PUT
            data = request.json or {}
            if not isinstance(data, dict):
                raise ValidationError("Request body must be a JSON object")
            if "name" in data:
                goal.name = validate_string(data["name"], "name")
            if "target_amount" in data:
                goal.target_amount = validate_float(data["target_amount"], "target_amount", min_val=0.01)
            if "current_amount" in data:
                goal.current_amount = validate_float(data["current_amount"], "current_amount", min_val=0.0)
            if "target_date" in data:
                goal.target_date = validate_string(data["target_date"], "target_date")
            db.session.commit()

            milestones = compute_monthly_milestones(goal)
            persist_goal_milestones(goal, milestones)

            return jsonify({"status": "success", "goal": goal.to_dict()})
    except ValidationError as e:
        raise e
    except Exception as e:
        return jsonify({"error": str(e)}), 400



@app.route("/api/goals", methods=["GET"])
def get_goals():
    try:
        goals = FinancialGoal.query.order_by(FinancialGoal.created_at.desc()).all()
        goals_list = [g.to_dict() for g in goals]

        # Add AI recommendations if available
        ai_recommendations = {}
        if client and len(goals_list) > 0:
            for goal in goals_list:
                remaining = goal["target_amount"] - goal["current_amount"]
                if remaining > 0:
                    try:
                        # Calculate monthly savings needed
                        from datetime import datetime
                        target_dt = datetime.strptime(goal["target_date"], "%Y-%m")
                        now = datetime.now()
                        months_remaining = (target_dt.year - now.year) * 12 + (target_dt.month - now.month)
                        if months_remaining <= 0:
                            months_remaining = 1

                        monthly_needed = remaining / months_remaining
                        prompt = (
                            f"Goal: {goal['name']}\n"
                            f"Target amount: ₹{goal['target_amount']:,}\n"
                            f"Current saved: ₹{goal['current_amount']:,}\n"
                            f"Remaining: ₹{remaining:,}\n"
                            f"Months remaining: {months_remaining}\n"
                            f"Required monthly savings: ₹{monthly_needed:,.2f}\n\n"
                            f"Give 3-4 practical, actionable tips to reach this financial goal faster in India. Keep it concise."
                        )
                        res = client.chat.completions.create(
                            model="llama-3.1-8b-instant",
                            messages=[
                                {"role": "system", "content": "You are a helpful Indian personal finance advisor."},
                                {"role": "user", "content": prompt}
                            ]
                        )
                        ai_recommendations[goal["id"]] = res.choices[0].message.content.strip()
                    except Exception as ai_err:
                        app.logger.error(f"Goal AI Recommendation Error: {str(ai_err)}")
                        ai_recommendations[goal["id"]] = "AI recommendations unavailable."

        return jsonify({"goals": goals_list, "ai_recommendations": ai_recommendations})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ---------------- SCHEDULER ----------------
from apscheduler.schedulers.background import BackgroundScheduler

def check_all_budgets_job():
    with app.app_context():
        import datetime
        ym = datetime.datetime.now().strftime("%Y-%m")
        limits = BudgetLimit.query.all()
        for limit in limits:
            run_threshold_checks(limit.category, ym)

def check_stock_alerts_job():
    with app.app_context():
        alerts = PriceAlert.query.filter_by(is_triggered=False).all()
        for alert in alerts:
            res = get_stock_price(alert.symbol)
            if res and "price" in res and "error" not in res:
                current_price = res["price"]
                triggered = False
                if alert.condition == "above" and current_price >= alert.target_price:
                    triggered = True
                elif alert.condition == "below" and current_price <= alert.target_price:
                    triggered = True
                
                if triggered:
                    alert.is_triggered = True
                    print(
                        f"\n[STOCK ALERT] Triggered for {alert.symbol}\n"
                        f"Condition: {alert.condition} {alert.target_price}\n"
                        f"Current Price: {current_price}\n",
                        file=sys.stderr
                    )
        db.session.commit()

if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_all_budgets_job, 'interval', days=1)
    scheduler.add_job(check_stock_alerts_job, 'interval', minutes=10)
    scheduler.start()

# ---------------- RUN ----------------
if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "yes")
    app.run(debug=debug_mode)



from flask import Flask, request, jsonify, render_template
import yfinance as yf 
import os
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set default API key ONLY if not already defined in environment
if not os.getenv("GROQ_API_KEY"):
    os.environ["GROQ_API_KEY"] = "YOUR_API_KEY"
# ---------------- IMPORT UTILS ----------------
from utils.sip import calculate_sip
from utils.tax import calculate_tax
from utils.pdf_parser import extract_income
from utils.money_score import calculate_money_score
from utils.multi_agent import run_multi_agent
from utils.stock import get_stock_price
from utils.expense_track import calculate_expense, insights

app = Flask(__name__)

# ---------------- INIT GROQ ----------------
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("index.html")


# ---------------- 🤖 AI CHAT ----------------
@app.route("/chat", methods=["POST"])
def chat():
    try:
        msg = request.json.get("message")

        res = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a financial advisor for India."},
                {"role": "user", "content": msg}
            ]
        )

        return jsonify({"reply": res.choices[0].message.content})

    except Exception as e:
        return jsonify({"reply": f"Error: {str(e)}"})


# ---------------- 💸 SIP ----------------
@app.route("/sip", methods=["POST"])
def sip():
    try:
        data = request.json
        result = calculate_sip(
            float(data["monthly"]),
            float(data["rate"]),
            int(data["years"])
        )
        return jsonify({"future_value": result})

    except Exception as e:
        return jsonify({"error": str(e)})


# ---------------- 📊 STOCK ----------------
@app.route("/portfolio", methods=["POST"])
def portfolio():
    try:
        stock = request.json["stock"].upper()
        result = get_stock_price(stock)
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)})
    
# ---------------- 💸 TAX ----------------
@app.route("/tax", methods=["POST"])
def tax():
    try:
        income = float(request.json["income"])
        return jsonify({"tax": calculate_tax(income)})

    except Exception as e:
        return jsonify({"error": str(e)})


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
    try:
        query = request.json["query"]
        response = run_multi_agent(client, query)
        return jsonify({"response": response})

    except Exception as e:
        return jsonify({"error": str(e)})


# ---------------- 💰 MONEY SCORE ----------------
@app.route("/money-score", methods=["POST"])
def money_score():
    try:
        data = request.json

        score = calculate_money_score(
            float(data["income"]),
            float(data["expenses"]),
            float(data["savings"]),
            float(data["investments"]),
            float(data["debt"]),
            float(data["emergency"])
        )

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

    except Exception as e:
        return jsonify({"error": str(e)})


# Expense Tracker Features

expense_data = []

@app.route("/add_expense", methods=["POST"])
def add_expense():
    try:
        data = request.json
        expense = {
            "category": data["category"],
            "amount": float(data["amount"]),
            "date": data["date"]
        }
        expense_data.append(expense)
        return jsonify({"status": "success"})
    
    except Exception as e:
        return jsonify({"error": str(e)}),400

@app.route("/calculate", methods=["GET"])
def calculate():
    result = calculate_expense(expense_data)
    result["expenses"] = expense_data
    return jsonify(result)

@app.route("/insights", methods=["GET"])
def expense_insights():
    result =insights(client,expense_data)
    return jsonify(result)

# ---------------- NET WORTH TRACKER ----------------
# Net Worth Tracker Features
assets_data = []
liabilities_data = []

@app.route("/net-worth", methods=["GET", "POST"])
def get_net_worth():
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
        data = request.json
        assets_data.append({
            "id": len(assets_data),
            "name": data["name"],
            "amount": float(data["amount"])
        })
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/add-liability", methods=["POST"])
def add_liability():
    try:
        data = request.json
        liabilities_data.append({
            "id": len(liabilities_data),
            "name": data["name"],
            "amount": float(data["amount"])
        })
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/delete-item", methods=["POST"])
def delete_item():
    try:
        data = request.json
        item_type = data["type"] # 'asset' or 'liability'
        item_id = int(data["id"])

        if item_type == 'asset':
            assets_data.pop(item_id)
        else:
            liabilities_data.pop(item_id)

        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)

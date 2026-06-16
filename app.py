from flask import Flask, request, jsonify, render_template
from flask_mail import Mail, Message
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
import sqlite3
import atexit
import yfinance as yf
import os
import sys
from groq import Groq
from dotenv import load_dotenv

# Load environment variables from .env file (if present)
load_dotenv()

# ── Startup validation ───────────────────────────────────────
# Fail fast and clearly if the required API key is missing.
# Copy .env.example → .env and set your GROQ_API_KEY.
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY or GROQ_API_KEY.strip() in ("", "your_groq_api_key_here"):
    print(
        "\n[ERROR] GROQ_API_KEY is not configured.\n"
        "  1. Copy .env.example to .env\n"
        "  2. Set your GROQ_API_KEY in .env\n"
        "  Obtain a free key at: https://console.groq.com/\n",
        file=sys.stderr,
    )
    sys.exit(1)

# ---------------- IMPORT UTILS ----------------
from utils.sip import calculate_sip
from utils.tax import calculate_tax
from utils.pdf_parser import extract_income
from utils.money_score import calculate_money_score
from utils.multi_agent import run_multi_agent
from utils.stock import get_stock_price
from utils.expense_track import calculate_expense, insights

app = Flask(__name__)

# ============================================
# EMAIL CONFIGURATION
# ============================================
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('EMAIL_USER', 'your-email@gmail.com')  # Change this
app.config['MAIL_PASSWORD'] = os.getenv('EMAIL_PASS', 'your-app-password')     # Change this
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('EMAIL_USER', 'your-email@gmail.com')

mail = Mail(app)

# ============================================
# DATABASE FUNCTIONS FOR EMAIL SETTINGS
# ============================================
def init_email_db():
    """Create email settings table if not exists"""
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email VARCHAR(120) UNIQUE,
            weekly_email_enabled BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def get_user_email_settings():
    """Get all users with email enabled"""
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT email FROM user_settings WHERE weekly_email_enabled = 1')
    users = c.fetchall()
    conn.close()
    return [user[0] for user in users]

# Initialize email database
init_email_db()

# ============================================
# WEEKLY REPORT GENERATOR
# ============================================
def generate_weekly_report(user_email):
    """Generate weekly financial report for a user"""
    # For now, return sample data
    # In production, fetch from database
    return {
        'date': datetime.now().strftime('%B %d, %Y'),
        'total_spend': '₹12,450',
        'spend_change': '+5.2',
        'spend_change_class': 'positive' if 5.2 > 0 else 'negative',
        'net_worth': '₹4,28,500',
        'net_worth_change': '+2.1',
        'budget_health': '85%',
        'budget_health_class': 'positive' if 85 > 70 else 'negative',
        'budget_health_text': 'On Track ✅' if 85 > 70 else 'Over Budget ⚠️',
        'top_category': 'Food',
        'top_category_amount': '₹4,200',
        'top_categories': {
            'Food': '₹4,200',
            'Transport': '₹2,800',
            'Shopping': '₹1,900',
            'Entertainment': '₹1,500'
        },
        'ai_insight': 'You spent 40% more on dining out this week. Try cooking 2 extra meals at home to save ₹600.',
        'dashboard_url': 'http://localhost:5000/dashboard',
        'opt_out_url': 'http://localhost:5000/settings'
    }

def send_weekly_email(user_email):
    """Send weekly report email to a user"""
    try:
        report_data = generate_weekly_report(user_email)
        
        msg = Message(
            subject=f"📊 Weekly Financial Digest - {datetime.now().strftime('%B %d, %Y')}",
            recipients=[user_email],
            html=render_template('weekly_report.html', **report_data)
        )
        mail.send(msg)
        print(f"✅ Email sent to {user_email}")
        return True
    except Exception as e:
        print(f"❌ Failed to send email to {user_email}: {e}")
        return False

def send_weekly_reports():
    """Send weekly reports to all users"""
    print("🔄 Running weekly email job...")
    users = get_user_email_settings()
    
    if not users:
        print("📭 No users subscribed to weekly emails")
        return
    
    success = 0
    for user_email in users:
        if send_weekly_email(user_email):
            success += 1
    
    print(f"✅ Sent {success}/{len(users)} weekly reports")

# ============================================
# SCHEDULER - Runs every Monday at 9:00 AM
# ============================================
scheduler = BackgroundScheduler()

scheduler.add_job(
    func=send_weekly_reports,
    trigger=CronTrigger(day_of_week='mon', hour=9, minute=0),
    id='weekly_email_job',
    replace_existing=True
)
scheduler.start()

# Shutdown scheduler on app exit
atexit.register(lambda: scheduler.shutdown())

# ---------------- INIT DATABASE ----------------
from models import db, Expense, Asset, Liability

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///money_mentor.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

with app.app_context():
    db.create_all()

# ---------------- INIT GROQ ----------------
client = Groq(api_key=GROQ_API_KEY)

# ── Dev-mode startup message ─────────────────────────────────
if os.getenv("FLASK_ENV", "development") != "production":
    print("[OK] Groq client initialised successfully.")

# ============================================
# ROUTES
# ============================================

# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("index.html")

# ---------------- RETIREMENT ----------------
@app.route('/retirement')
def retirement():
    """Retirement & Inflation Simulator Page"""
    return render_template('retirement.html')

# ---------------- SETTINGS ----------------
@app.route('/settings')
def settings():
    """User settings page"""
    return render_template('settings.html')

@app.route('/api/update-email', methods=['POST'])
def update_email():
    """Update user email settings"""
    data = request.json
    email = data.get('email')
    enabled = data.get('enabled', True)
    
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    c.execute('''
        INSERT OR REPLACE INTO user_settings (email, weekly_email_enabled)
        VALUES (?, ?)
    ''', (email, 1 if enabled else 0))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Settings updated successfully'})

@app.route('/api/unsubscribe', methods=['POST'])
def unsubscribe():
    """Unsubscribe from weekly emails"""
    data = request.json
    email = data.get('email')
    
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('UPDATE user_settings SET weekly_email_enabled = 0 WHERE email = ?', (email,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Unsubscribed successfully'})

# ---------------- TEST EMAIL ROUTES ----------------
@app.route('/test-email')
def test_email():
    """Send a test email to verify configuration"""
    email = os.getenv('EMAIL_USER', 'your-email@gmail.com')
    send_weekly_email(email)
    return "Test email sent! Check your inbox."

@app.route('/force-weekly')
def force_weekly():
    """Force send weekly reports (for testing)"""
    send_weekly_reports()
    return "Weekly reports sent manually!"

# ---------------- HEALTH CHECK ----------------
@app.route("/health", methods=["GET"])
def health_check():
    """Lightweight liveness probe for deployment environments (Docker, Railway, etc.)."""
    return jsonify({"status": "ok", "service": "AI Money Mentor"}), 200

# ---------------- ERROR HANDLERS ----------------
@app.errorhandler(400)
def bad_request(error):
    return jsonify({
        "error": "Bad Request",
        "message": str(error),
        "status_code": 400
    }), 400

@app.errorhandler(404)
def not_found(error):
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
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.json
        msg = data.get("message")
        history = data.get("history", [])

        messages = [{"role": "system", "content": "You are a financial advisor for India."}]
        messages += history[-10:]
        messages.append({"role": "user", "content": msg})

        res = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages
        )

        return jsonify({
            "reply": res.choices[0].message.content
        })

    except Exception as e:
        app.logger.error(f"Groq API Error: {str(e)}")
        return jsonify({
            "reply": "Unable to generate a response at the moment. Please try again later."
        }), 500

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

# ---------------- EXPENSE TRACKER ----------------
@app.route("/add_expense", methods=["POST"])
def add_expense():
    try:
        data = request.json
        expense = Expense(
            category=data["category"],
            amount=float(data["amount"]),
            date=data["date"]
        )
        db.session.add(expense)
        db.session.commit()
        return jsonify({"status": "success"})

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
    result = insights(client, expense_data)
    return jsonify(result)

# ---------------- NET WORTH TRACKER ----------------
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
        data = request.json
        asset = Asset(name=data["name"], amount=float(data["amount"]))
        db.session.add(asset)
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/add-liability", methods=["POST"])
def add_liability():
    try:
        data = request.json
        liability = Liability(name=data["name"], amount=float(data["amount"]))
        db.session.add(liability)
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/delete-item", methods=["POST"])
def delete_item():
    try:
        data = request.json
        item_type = data["type"]
        item_id = int(data["id"])

        if item_type == 'asset':
            rows = Asset.query.order_by(Asset.id).all()
            db.session.delete(rows[item_id])
        else:
            rows = Liability.query.order_by(Liability.id).all()
            db.session.delete(rows[item_id])

        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# ---------------- RUN ----------------
if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "yes")
    app.run(debug=debug_mode)
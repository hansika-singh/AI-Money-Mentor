import datetime
from sqlalchemy import text
from models import db, User, Tutorial, Quiz, Question, UserQuizAttempt, UserTutorialProgress, UserChallenge, Expense, Portfolio, FinancialGoal

def seed_educational_content():
    """Seed tutorials, quizzes, and questions if they do not already exist."""
    # 1. Seed Tutorials
    tutorials_data = [
        {
            "id": 1,
            "title": "Understanding Mutual Funds",
            "description": "Learn the basics of mutual funds, NAV, expense ratio, and how to choose active vs passive funds.",
            "category": "Mutual Funds",
            "content": """### What is a Mutual Fund?
A mutual fund is a pool of money managed by a professional fund manager. It collects money from multiple investors and invests it in equities, bonds, money market instruments, and other assets.

#### Key Concepts:
1. **NAV (Net Asset Value)**: This represents the market value per share/unit of the mutual fund. It is calculated at the close of each trading day.
   $$\\text{NAV} = \\frac{\\text{Total Assets} - \\text{Total Liabilities}}{\\text{Total Outstanding Shares}}$$
2. **Expense Ratio**: The annual fee charged by the fund to cover its management and operating expenses. A lower expense ratio means more of your money goes towards actual investment growth.
3. **Active vs. Passive Funds**:
   * **Active Funds**: A fund manager actively picks stocks to beat a benchmark index. These have higher fees.
   * **Passive (Index) Funds**: These simply copy/track a market index (like Nifty 50 or S&P 500). They have much lower fees and often outperform active funds over the long term.

#### Diversification
The biggest advantage of mutual funds is instant diversification. Instead of buying one stock, your ₹1,000 investment buys a fraction of 50+ different companies, protecting you if a few companies fail.""",
            "points_reward": 15
        },
        {
            "id": 2,
            "title": "How to Read a Stock Chart",
            "description": "Unlock the secrets of candlestick charts, trendlines, support/resistance, and technical indicators.",
            "category": "Stock Charts",
            "content": """### Basics of Technical Analysis
While fundamental analysis looks at a company's financial health, technical analysis examines historical price and volume movements, typically displayed on stock charts.

#### Candlestick Charts
Each candlestick represents price action over a specific period (e.g., 1 day):
* **Body**: The thick part showing the opening and closing prices.
  * **Green (Bullish)**: Price closed higher than it opened.
  * **Red (Bearish)**: Price closed lower than it opened.
* **Wicks (Shadows)**: The thin lines extending above/below the body showing the highest and lowest prices reached during that period.

#### Support & Resistance
* **Support**: A price level where a stock price tends to find buying interest and stop falling. Think of it as a floor.
* **Resistance**: A price level where a stock struggles to rise above because of selling pressure. Think of it as a ceiling.

#### Simple Moving Averages (SMA)
An SMA averages a stock's price over a set period (like 50 or 200 days). It smoothes out short-term noise and helps you see the overall direction of the trend. When a short-term moving average crosses above a long-term one, it's often viewed as a bullish sign.""",
            "points_reward": 15
        },
        {
            "id": 3,
            "title": "The Power of Compounding",
            "description": "Discover how compound interest works, the Rule of 72, and the life-changing impact of starting early.",
            "category": "Investing",
            "content": """### What is Compounding?
Albert Einstein famously called compound interest the 'eighth wonder of the world'. It is the process where your investment earns interest, and then that interest earns interest, compounding your returns over time.

#### The Rule of 72
A quick mental math shortcut to find how long it takes to double your money:
$$\\text{Years to Double} = \\frac{72}{\\text{Annual Rate of Return}}$$
* E.g., at an **8%** annual return: $72 / 8 = 9$ years to double.
* At a **12%** annual return: $72 / 12 = 6$ years to double.

#### Starting Early: A Comparison
* **Investor A** starts investing ₹5,000/month at age 25. By age 55 (30 years), at an 10% return, they accumulate **₹1.13 Crores** (having invested ₹18 Lakhs).
* **Investor B** starts investing the same ₹5,000/month at age 35. By age 55 (20 years), at the same return, they accumulate only **₹38 Lakhs** (having invested ₹12 Lakhs).

By starting 10 years earlier, Investor A accumulates nearly **3x** the wealth with only 1.5x the money invested! That is the magic of time and compounding.""",
            "points_reward": 15
        },
        {
            "id": 4,
            "title": "Basics of Budgeting (50/30/20 Rule)",
            "description": "Master the 50/30/20 budget framework to separate needs, wants, and savings automatically.",
            "category": "Budgeting",
            "content": """### The 50/30/20 Budgeting Rule
If tracking every single rupee feels overwhelming, the 50/30/20 rule is a simple, intuitive framework to manage your after-tax income.

#### 1. Needs (50%)
Half of your income should go to essentials you cannot live without:
* Rent/Mortgage payments
* Groceries and basic food
* Utilities (electricity, water, internet)
* Insurance & minimum debt repayments

#### 2. Wants (30%)
Discretionary expenses that enhance your life but are not strictly necessary:
* Dining out and entertainment
* Hobbies and gym memberships
* Travel and luxury shopping
* Subscription services (Netflix, Spotify)

#### 3. Savings & Investments (20%)
The remaining 20% should be immediately funneled towards your future self:
* Emergency fund building (3-6 months of expenses)
* Retirement investments (EPF, PPF, Mutual Funds)
* Extra payments to pay off high-interest debt quickly

#### How to Implement It
Start by listing your net take-home income. Immediately redirect 20% to your savings/investment account at the start of the month (known as 'paying yourself first'). Then pay your fixed needs, and spend whatever is left on your wants guilt-free!""",
            "points_reward": 15
        }
    ]

    for t_data in tutorials_data:
        existing = Tutorial.query.get(t_data["id"])
        if not existing:
            t = Tutorial(
                id=t_data["id"],
                title=t_data["title"],
                description=t_data["description"],
                content=t_data["content"],
                category=t_data["category"],
                points_reward=t_data["points_reward"]
            )
            db.session.add(t)
    db.session.commit()

    # 2. Seed Quizzes
    quizzes_data = [
        {
            "id": 1,
            "title": "Mutual Funds Quiz",
            "description": "Test your knowledge on Net Asset Value, expense ratios, and active vs passive investing.",
            "points_reward": 20,
            "questions": [
                {
                    "question_text": "What does NAV stand for in Mutual Funds?",
                    "option_a": "Net Asset Value",
                    "option_b": "Net Accumulated Venture",
                    "option_c": "Nominal Asset Value",
                    "option_d": "National Auto Valuation",
                    "correct_option": "A",
                    "explanation": "NAV stands for Net Asset Value. It represents the per-share market value of a mutual fund's assets minus its liabilities."
                },
                {
                    "question_text": "Which type of mutual fund typically tracks a market index (like Nifty 50) with lower fees?",
                    "option_a": "Active Fund",
                    "option_b": "Index Fund",
                    "option_c": "Sector Fund",
                    "option_d": "Liquid Fund",
                    "correct_option": "B",
                    "explanation": "Index funds passively track a market index, meaning they require no active picking of stocks. This keeps management fees (expense ratios) extremely low."
                },
                {
                    "question_text": "What is the 'expense ratio' in a mutual fund?",
                    "option_a": "The penalty charged for early withdrawal from a fund",
                    "option_b": "The ratio of a fund's debt to its equity investments",
                    "option_c": "The annual percentage fee charged by the fund to manage your money",
                    "option_d": "The taxes paid on mutual fund returns",
                    "correct_option": "C",
                    "explanation": "The expense ratio measures how much of a fund's assets are used for administrative, management, advertising, and all other operating expenses annually."
                }
            ]
        },
        {
            "id": 2,
            "title": "Stock Charts Quiz",
            "description": "Show your skills in technical analysis, reading candlesticks, and spotting support levels.",
            "points_reward": 20,
            "questions": [
                {
                    "question_text": "In a candlestick chart, what does a green candlestick typically represent?",
                    "option_a": "The stock price closed lower than it opened",
                    "option_b": "The stock price closed higher than it opened",
                    "option_c": "The stock is suspended from trading",
                    "option_d": "The trading volume was extremely low",
                    "correct_option": "B",
                    "explanation": "A green candlestick represents a bullish period, meaning that the closing price of the stock was higher than its opening price."
                },
                {
                    "question_text": "What is 'Support' in technical chart analysis?",
                    "option_a": "A price ceiling where a stock struggles to rise above",
                    "option_b": "Financial assistance provided to a listed company by the government",
                    "option_c": "A price level where a stock price tends to find buying interest and stop falling",
                    "option_d": "The customer helpline of the stock exchange",
                    "correct_option": "C",
                    "explanation": "Support acts as a 'floor' for a stock price because buying demand increases and matches or exceeds selling pressure at that level."
                },
                {
                    "question_text": "What does a Simple Moving Average (SMA) do on a stock chart?",
                    "option_a": "It predicts the exact future price of the stock",
                    "option_b": "It averages historical prices over a period to smooth out noise and show the trend direction",
                    "option_c": "It calculates the company's total debt-to-equity ratio",
                    "option_d": "It tracks inflation rates in the stock's host country",
                    "correct_option": "B",
                    "explanation": "An SMA averages past closing prices over a specific number of days, helping traders spot the general trend direction without being distracted by daily volatility."
                }
            ]
        },
        {
            "id": 3,
            "title": "Compounding Quiz",
            "description": "Calculate doubling periods and test your comprehension of compound interest.",
            "points_reward": 20,
            "questions": [
                {
                    "question_text": "According to the Rule of 72, if you earn an 8% annual return, how long will it take to double your money?",
                    "option_a": "8 years",
                    "option_b": "9 years",
                    "option_c": "12 years",
                    "option_d": "72 years",
                    "correct_option": "B",
                    "explanation": "Divide 72 by the annual return percentage: 72 / 8 = 9 years to double your initial investment."
                },
                {
                    "question_text": "What is compound interest?",
                    "option_a": "Interest calculated only on the initial principal amount",
                    "option_b": "Interest calculated on the principal plus all accumulated interest from prior periods",
                    "option_c": "A penalty fee for paying bills late",
                    "option_d": "Tax interest paid to local authorities",
                    "correct_option": "B",
                    "explanation": "Compound interest is 'interest on interest'. It builds exponentially because you earn interest on both your starting capital and the returns it has already earned."
                }
            ]
        },
        {
            "id": 4,
            "title": "Budgeting Quiz",
            "description": "Test your application of the 50/30/20 budgeting framework.",
            "points_reward": 20,
            "questions": [
                {
                    "question_text": "Under the 50/30/20 rule, which category should receive 50% of your income?",
                    "option_a": "Wants",
                    "option_b": "Savings & Investments",
                    "option_c": "Needs",
                    "option_d": "Emergencies",
                    "correct_option": "C",
                    "explanation": "The rule allocates 50% of take-home income to essential Needs (rent/mortgage, utilities, groceries, basic transportation)."
                },
                {
                    "question_text": "Which of the following is considered a 'Want' rather than a 'Need'?",
                    "option_a": "Rent payment",
                    "option_b": "Weekly groceries",
                    "option_c": "Basic health insurance",
                    "option_d": "Dining out at a fancy restaurant",
                    "correct_option": "D",
                    "explanation": "Rent, health insurance, and basic groceries are essential Needs. Dining out at a fancy restaurant is discretionary spending (Want)."
                }
            ]
        }
    ]

    for q_data in quizzes_data:
        existing_q = Quiz.query.get(q_data["id"])
        if not existing_q:
            q = Quiz(
                id=q_data["id"],
                title=q_data["title"],
                description=q_data["description"],
                points_reward=q_data["points_reward"]
            )
            db.session.add(q)
            db.session.flush()  # Get ID

            for question in q_data["questions"]:
                qn = Question(
                    quiz_id=q.id,
                    question_text=question["question_text"],
                    option_a=question["option_a"],
                    option_b=question["option_b"],
                    option_c=question["option_c"],
                    option_d=question["option_d"],
                    correct_option=question["correct_option"],
                    explanation=question["explanation"]
                )
                db.session.add(qn)
    db.session.commit()


def get_expense_streak(user_id):
    """
    Calculate the number of consecutive calendar days of logged expenses ending today or yesterday.
    Returns: (streak_count, list_of_dates)
    """
    expenses = Expense.query.filter_by(user_id=user_id).all()
    if not expenses:
        return 0, []

    # Parse and unique-ify expense dates
    dates = set()
    for e in expenses:
        try:
            # Assumes YYYY-MM-DD
            d = datetime.datetime.strptime(e.date, "%Y-%m-%d").date()
            dates.add(d)
        except Exception:
            continue

    if not dates:
        return 0, []

    sorted_dates = sorted(list(dates), reverse=True)
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)

    # Streak starts if the most recent expense is today or yesterday
    start_date = None
    if today in dates:
        start_date = today
    elif yesterday in dates:
        start_date = yesterday
    else:
        return 0, sorted_dates

    # Count consecutive days backwards
    streak = 1
    current = start_date
    while True:
        prev = current - datetime.timedelta(days=1)
        if prev in dates:
            streak += 1
            current = prev
        else:
            break

    return streak, sorted_dates


def check_and_update_challenges(user_id):
    """
    Check if the user has completed any gamified challenges.
    If newly completed, save the completion to UserChallenge, award points, and return list of completed keys.
    """
    newly_completed = []
    
    # 1. Consistent Tracker (7-day expense streak)
    streak, _ = get_expense_streak(user_id)
    if streak >= 7:
        newly_completed.append(("expense_streak_7", 50))

    # 2. Portfolio Builder (2+ portfolio entries)
    portfolio_count = Portfolio.query.filter_by(user_id=user_id).count()
    if portfolio_count >= 2:
        newly_completed.append(("portfolio_builder_2", 30))

    # 3. Goal Getter (Goal of ₹10k+ created)
    goals = FinancialGoal.query.filter_by(user_id=user_id).all()
    has_large_goal = any(g.target_amount >= 10000 for g in goals)
    if has_large_goal:
        newly_completed.append(("goal_getter", 20))

    completed_keys = []

    user = db.session.get(User, user_id)
    if not user:
        return []

    for key, points in newly_completed:
        # Check if already completed in DB
        existing = UserChallenge.query.filter_by(user_id=user_id, challenge_key=key).first()
        if not existing:
            # Complete challenge, award points
            uc = UserChallenge(user_id=user_id, challenge_key=key, completed=True)
            db.session.add(uc)
            user.points = (user.points or 0) + points
            completed_keys.append(key)

    if completed_keys:
        db.session.commit()

    return completed_keys

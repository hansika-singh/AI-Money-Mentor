import json
import datetime
from datetime import date, timedelta
import pytest
from app import app, db
from models import User, Tutorial, Quiz, Question, UserQuizAttempt, UserTutorialProgress, UserChallenge, Expense, Portfolio, FinancialGoal

@pytest.fixture
def client():
    # Clean and initialize test database structures
    with app.app_context():
        db.create_all()
        # Clean tables
        db.session.query(UserQuizAttempt).delete()
        db.session.query(UserTutorialProgress).delete()
        db.session.query(UserChallenge).delete()
        db.session.query(Expense).delete()
        db.session.query(Portfolio).delete()
        db.session.query(FinancialGoal).delete()
        
        # Ensure test user exists and has 0 points
        user = User.query.filter_by(email="test_edu@example.com").first()
        if not user:
            user = User(username="testeduuser", email="test_edu@example.com", password_hash="pbkdf2:sha256:260000$test", points=0)
            db.session.add(user)
        else:
            user.points = 0
        db.session.commit()
        user_id = user.id
        
    app.config["TESTING"] = True
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user_id)
            sess['_fresh'] = True
            
        yield client

    # Cleanup after test runs to avoid pollution
    with app.app_context():
        db.session.query(UserQuizAttempt).delete()
        db.session.query(UserTutorialProgress).delete()
        db.session.query(UserChallenge).delete()
        db.session.query(Expense).delete()
        db.session.query(Portfolio).delete()
        db.session.query(FinancialGoal).delete()
        user = User.query.filter_by(email="test_edu@example.com").first()
        if user:
            db.session.delete(user)
        db.session.commit()


def test_seeding(client):
    """Verify that tutorials and quizzes are seeded on app startup."""
    with app.app_context():
        tutorials = Tutorial.query.all()
        quizzes = Quiz.query.all()
        questions = Question.query.all()
        
        assert len(tutorials) >= 4
        assert len(quizzes) >= 4
        assert len(questions) >= 10


def test_learn_page(client):
    """Verify the learn view returns 200."""
    res = client.get("/learn")
    assert res.status_code == 200
    assert b"Learn &" in res.data


def test_get_tutorials(client):
    """Verify the get tutorials API returns all seeded tutorials."""
    res = client.get("/api/tutorials")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert "tutorials" in data
    assert len(data["tutorials"]) >= 4
    # All should initially be uncompleted
    for t in data["tutorials"]:
        assert t["completed"] is False


def test_complete_tutorial(client):
    """Verify reading a tutorial marks it complete and awards points."""
    # First attempt: should award points
    res = client.post("/api/tutorials/1/complete")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["success"] is True
    assert data["points_awarded"] == 15
    assert data["total_points"] == 15

    # Check user points directly in DB
    with app.app_context():
        user = User.query.filter_by(email="test_edu@example.com").first()
        assert user.points == 15
        
        progress = UserTutorialProgress.query.filter_by(user_id=user.id, tutorial_id=1).first()
        assert progress is not None
        assert progress.completed is True

    # Second attempt: should not award points again
    res = client.post("/api/tutorials/1/complete")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["success"] is True
    assert data["points_awarded"] == 0
    assert data["total_points"] == 15


def test_get_quizzes(client):
    """Verify the get quizzes API returns seeded quizzes with high scores."""
    res = client.get("/api/quizzes")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert "quizzes" in data
    assert len(data["quizzes"]) >= 4
    for q in data["quizzes"]:
        assert q["high_score"] is None
        assert q["total_questions"] > 0


def test_get_quiz_questions(client):
    """Verify quiz questions API excludes correct options and explanations to avoid cheating."""
    res = client.get("/api/quizzes/1/questions")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert "quiz_title" in data
    assert "questions" in data
    assert len(data["questions"]) > 0
    
    # Check that answer key values are hidden from the questions payload
    for q in data["questions"]:
        assert "correct_option" not in q
        assert "explanation" not in q
        assert "option_a" in q
        assert "option_b" in q
        assert "option_c" in q
        assert "option_d" in q


def test_submit_quiz_flow(client):
    """Verify submitting quiz answers works and awards points incrementally."""
    # 1. Fetch questions for Quiz 1
    res = client.get("/api/quizzes/1/questions")
    data = json.loads(res.data)
    questions = data["questions"]
    
    # 2. Submit wrong answers (select D for all questions)
    answers = {str(q["id"]): "D" for q in questions}
    res = client.post("/api/quizzes/1/submit", json={"answers": answers})
    assert res.status_code == 200
    data = json.loads(res.data)
    
    assert data["success"] is True
    assert data["score"] == 0
    # First attempt gives 10 points attempt bonus
    assert data["points_awarded"] == 10 
    assert data["total_points"] == 10
    
    # 3. Submit all correct answers (fetch correct options from DB context)
    with app.app_context():
        correct_map = {q.id: q.correct_option for q in Question.query.filter_by(quiz_id=1).all()}
    
    correct_answers = {str(qid): correct_opt for qid, correct_opt in correct_map.items()}
    res = client.post("/api/quizzes/1/submit", json={"answers": correct_answers})
    assert res.status_code == 200
    data = json.loads(res.data)
    
    assert data["success"] is True
    assert data["score"] == len(questions)
    # Attempt bonus already awarded. So points = 0 (bonus) + 3 correct * 10 = 30 points.
    assert data["points_awarded"] == len(questions) * 10 
    assert data["total_points"] == 40  # 10 prior + 30 new points


def test_challenges_checking(client):
    """Verify that user challenges are correctly verified and points are awarded."""
    # Check initial challenges state
    res = client.get("/api/challenges")
    assert res.status_code == 200
    data = json.loads(res.data)
    for ch in data["challenges"]:
        assert ch["completed"] is False
        assert ch["progress"] == 0

    # 1. Test Portfolio Builder Challenge (needs 2+ portfolio entries)
    with app.app_context():
        user = User.query.filter_by(email="test_edu@example.com").first()
        p1 = Portfolio(user_id=user.id, symbol="RELIANCE.NS", name="Reliance Industries", quantity=5, buy_price=2400.0, buy_date="2026-06-01")
        p2 = Portfolio(user_id=user.id, symbol="TCS.NS", name="Tata Consultancy", quantity=2, buy_price=3200.0, buy_date="2026-06-02")
        db.session.add(p1)
        db.session.add(p2)
        db.session.commit()

    res = client.get("/api/challenges")
    data = json.loads(res.data)
    portfolio_challenge = next(ch for ch in data["challenges"] if ch["key"] == "portfolio_builder_2")
    assert portfolio_challenge["completed"] is True
    assert portfolio_challenge["progress"] == 2
    assert data["total_points"] == 30  # Got 30 points reward!

    # 2. Test Goal Setter Challenge (needs goal with ₹10k+ target)
    with app.app_context():
        user = User.query.filter_by(email="test_edu@example.com").first()
        goal = FinancialGoal(user_id=user.id, name="Buy Laptop", target_amount=15000, current_amount=0, target_date="2026-12-31")
        db.session.add(goal)
        db.session.commit()

    res = client.get("/api/challenges")
    data = json.loads(res.data)
    goal_challenge = next(ch for ch in data["challenges"] if ch["key"] == "goal_getter")
    assert goal_challenge["completed"] is True
    assert data["total_points"] == 50  # 30 prior + 20 new points!

    # 3. Test Consistent Tracker Challenge (needs 7 days expense streak)
    with app.app_context():
        user = User.query.filter_by(email="test_edu@example.com").first()
        today = datetime.date.today()
        for i in range(7):
            expense_date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            e = Expense(user_id=user.id, category="Food", amount=100.0, date=expense_date)
            db.session.add(e)
        db.session.commit()

    res = client.get("/api/challenges")
    data = json.loads(res.data)
    streak_challenge = next(ch for ch in data["challenges"] if ch["key"] == "expense_streak_7")
    assert streak_challenge["completed"] is True
    assert streak_challenge["progress"] == 7
    assert data["total_points"] == 100  # 50 prior + 50 new points!


def test_achievements_unlocking(client):
    """Verify that achievements are unlocked and returned correctly based on education hub progress."""
    # Initially user has no education achievements
    res = client.get("/api/achievements")
    data = json.loads(res.data)
    # Since they have no expenses either, they get "The Beginning" fallback
    assert len(data["achievements"]) == 1
    assert data["achievements"][0]["title"] == "The Beginning"

    # 1. Complete one tutorial -> Unlocks Scholar badge
    client.post("/api/tutorials/1/complete")
    res = client.get("/api/achievements")
    data = json.loads(res.data)
    titles = [ach["title"] for ach in data["achievements"]]
    assert "Scholar" in titles
    assert "Financial Guru" not in titles

    # 2. Complete two more tutorials -> Unlocks Financial Guru badge
    client.post("/api/tutorials/2/complete")
    client.post("/api/tutorials/3/complete")
    res = client.get("/api/achievements")
    data = json.loads(res.data)
    titles = [ach["title"] for ach in data["achievements"]]
    assert "Scholar" in titles
    assert "Financial Guru" in titles

    # 3. Attempt a quiz -> Unlocks Sharp Brain badge
    with app.app_context():
        user = User.query.filter_by(email="test_edu@example.com").first()
        # Mocking quiz attempt
        attempt = UserQuizAttempt(user_id=user.id, quiz_id=1, score=1, total_questions=3)
        db.session.add(attempt)
        db.session.commit()
    res = client.get("/api/achievements")
    data = json.loads(res.data)
    titles = [ach["title"] for ach in data["achievements"]]
    assert "Sharp Brain" in titles
    assert "Perfect Score" not in titles

    # 4. Score 100% on a quiz -> Unlocks Perfect Score badge
    with app.app_context():
        user = User.query.filter_by(email="test_edu@example.com").first()
        # Mocking 100% quiz attempt
        attempt = UserQuizAttempt(user_id=user.id, quiz_id=1, score=3, total_questions=3)
        db.session.add(attempt)
        db.session.commit()
    res = client.get("/api/achievements")
    data = json.loads(res.data)
    titles = [ach["title"] for ach in data["achievements"]]
    assert "Perfect Score" in titles

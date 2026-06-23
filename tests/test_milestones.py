import json
import pytest
from datetime import datetime
from app import app, db, check_sip_due_reminders, run_threshold_checks
from models import FinancialGoal, BudgetLimit, BudgetAlert, SipSchedule, MilestoneNotification


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            from models import User
            user = User.query.filter_by(email="test@example.com").first()
            if not user:
                user = User(username="testuser", email="test@example.com", password_hash="pbkdf2:sha256:260000$test")
                db.session.add(user)
                db.session.commit()
            user_id = user.id
            
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user_id)
            sess['_fresh'] = True
            
        yield client
        
        with app.app_context():
            db.drop_all()


def test_goal_milestones_trigger(client):
    # 1. Create goal with 10% progress (₹10k of ₹100k target)
    res = client.post("/goals", json={
        "name": "Trip to Europe",
        "target_amount": 100000.0,
        "current_amount": 10000.0,
        "currency": "INR",
        "target_date": "2026-12"
    })
    assert res.status_code == 201 or res.status_code == 200
    goal_id = json.loads(res.data)["goal"]["id"]

    # Verify no milestones triggered yet (10% < 25%)
    with app.app_context():
        notifs = MilestoneNotification.query.all()
        assert len(notifs) == 0

    # 2. Update current_amount to ₹30,000 (30% progress -> crosses 25%)
    res = client.put(f"/goals/{goal_id}", json={
        "current_amount": 30000.0
    })
    assert res.status_code == 200

    # Verify 25% milestone notification triggered
    with app.app_context():
        notifs = MilestoneNotification.query.order_by(MilestoneNotification.triggered_at.desc()).all()
        assert len(notifs) == 1
        assert notifs[0].category == "goal"
        assert notifs[0].ref_id == goal_id
        assert notifs[0].milestone_value == 25.0
        assert "25%" in notifs[0].title

    # 3. Update current_amount to ₹60,000 (60% progress -> crosses 50%)
    res = client.put(f"/goals/{goal_id}", json={
        "current_amount": 60000.0
    })
    assert res.status_code == 200

    # Verify 50% milestone notification triggered, and total goal milestones is 2 (25%, 50%)
    with app.app_context():
        notifs = MilestoneNotification.query.order_by(MilestoneNotification.triggered_at.desc()).all()
        assert len(notifs) == 2
        assert notifs[0].milestone_value == 50.0
        assert notifs[1].milestone_value == 25.0


def test_budget_milestones_trigger(client):
    # 1. Create a budget limit for "Food" (₹1,000 limit)
    res = client.post("/budget/limits", json={
        "category": "Food",
        "limit_amount": 1000.0,
        "currency": "INR"
    })
    assert res.status_code == 200

    # 2. Add an expense of ₹850 (85% of limit -> crosses 80% threshold)
    with app.app_context():
        from models import User, Expense
        user = User.query.filter_by(email="test@example.com").first()
        exp = Expense(
            user_id=user.id,
            category="Food",
            amount=850.0,
            currency="INR",
            date=datetime.now().strftime("%Y-%m-%d")
        )
        db.session.add(exp)
        db.session.commit()

        # Run threshold checks
        run_threshold_checks(user.id, "Food")

        # Verify budget milestone generated
        notifs = MilestoneNotification.query.filter_by(category="budget").all()
        assert len(notifs) == 1
        assert notifs[0].milestone_value == 80.0
        assert "80%" in notifs[0].title


def test_sip_schedules_and_milestones(client):
    # 1. Create SIP schedule (₹6,000 monthly contribution)
    res = client.post("/api/sip/schedules", json={
        "name": "Nifty Index Fund",
        "amount": 6000.0,
        "day_of_month": 5,
        "currency": "INR"
    })
    assert res.status_code == 201
    sip_id = json.loads(res.data)["id"]

    # 2. Verify listing
    res = client.get("/api/sip/schedules")
    assert res.status_code == 200
    sips = json.loads(res.data)
    assert len(sips) == 1
    assert sips[0]["name"] == "Nifty Index Fund"
    assert sips[0]["total_invested"] == 0.0

    # 3. Pay installment 1 (Total invested becomes ₹6,000)
    res = client.post(f"/api/sip/schedules/{sip_id}/pay")
    assert res.status_code == 200
    assert json.loads(res.data)["schedule"]["total_invested"] == 6000.0

    with app.app_context():
        notifs = MilestoneNotification.query.filter_by(category="sip").all()
        assert len(notifs) == 0

    # 4. Pay installment 2 (Total invested becomes ₹12,000 -> crosses ₹10,000 milestone)
    res = client.post(f"/api/sip/schedules/{sip_id}/pay")
    assert res.status_code == 200
    assert json.loads(res.data)["schedule"]["total_invested"] == 12000.0

    # Verify compounding milestone notification was generated
    with app.app_context():
        notifs = MilestoneNotification.query.filter_by(category="sip").all()
        assert len(notifs) == 1
        assert notifs[0].milestone_value == 10000.0
        assert "10,000" in notifs[0].message

    # 5. Delete SIP schedule
    res = client.delete(f"/api/sip/schedules/{sip_id}")
    assert res.status_code == 200

    res = client.get("/api/sip/schedules")
    assert len(json.loads(res.data)) == 0


def test_sip_due_reminders_job(client):
    # 1. Create a SIP schedule due on today's day of month
    import datetime
    today = datetime.date.today()
    
    with app.app_context():
        from models import User
        user = User.query.filter_by(email="test@example.com").first()
        sip = SipSchedule(
            user_id=user.id,
            name="Emergency Fund SIP",
            amount=5000.0,
            day_of_month=today.day,
            currency="INR",
            is_active=True
        )
        db.session.add(sip)
        db.session.commit()

    # 2. Run the SIP reminders job
    check_sip_due_reminders()

    # Verify due reminder notification created
    with app.app_context():
        notifs = MilestoneNotification.query.filter_by(category="sip").all()
        assert len(notifs) == 1
        assert "Due" in notifs[0].title
        assert notifs[0].milestone_value == float(today.year * 100 + today.month)

    # 3. Run job again - should NOT trigger duplicate notification
    check_sip_due_reminders()
    
    with app.app_context():
        notifs = MilestoneNotification.query.filter_by(category="sip").all()
        assert len(notifs) == 1


def test_milestone_read_endpoints(client):
    # Setup: manually create milestone notifications
    with app.app_context():
        from models import User
        user = User.query.filter_by(email="test@example.com").first()
        n1 = MilestoneNotification(user_id=user.id, title="Test 1", message="Msg 1", category="goal", is_read=False)
        n2 = MilestoneNotification(user_id=user.id, title="Test 2", message="Msg 2", category="sip", is_read=False)
        db.session.add_all([n1, n2])
        db.session.commit()
        n1_id = n1.id

    # 1. Get unread only
    res = client.get("/api/milestones?unread_only=true")
    assert res.status_code == 200
    unread = json.loads(res.data)
    assert len(unread) == 2

    # 2. Mark one as read
    res = client.post("/api/milestones/read", json={"id": n1_id})
    assert res.status_code == 200

    res = client.get("/api/milestones?unread_only=true")
    unread = json.loads(res.data)
    assert len(unread) == 1
    assert unread[0]["title"] == "Test 2"

    # 3. Mark all as read
    res = client.post("/api/milestones/read", json={})
    assert res.status_code == 200

    res = client.get("/api/milestones?unread_only=true")
    unread = json.loads(res.data)
    assert len(unread) == 0

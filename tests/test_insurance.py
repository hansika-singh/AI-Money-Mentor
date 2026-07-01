import json
import pytest
from app import app, db
from models import User, InsurancePolicy, InsuranceRecommendation
from utils.insurance_planner import calculate_hlv, recommend_health_cover
from utils.multi_agent import route_query

@pytest.fixture
def client():
    # Save database state by cleaning testing tables
    with app.app_context():
        db.create_all()
        # Clean target tables
        db.session.query(InsurancePolicy).delete()
        db.session.query(InsuranceRecommendation).delete()
        
        # Ensure test user exists
        user = User.query.filter_by(email="test_ins@example.com").first()
        if not user:
            user = User(username="testinsuser", email="test_ins@example.com", password_hash="pbkdf2:sha256:260000$test")
            db.session.add(user)
        db.session.commit()
        user_id = user.id
        
    app.config["TESTING"] = True
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user_id)
            sess['_fresh'] = True
            
        yield client

    # Cleanup database context
    with app.app_context():
        db.session.query(InsurancePolicy).delete()
        db.session.query(InsuranceRecommendation).delete()
        user = User.query.filter_by(email="test_ins@example.com").first()
        if user:
            db.session.delete(user)
        db.session.commit()


def test_calculations():
    """Verify Human Life Value and health cover recommendations."""
    # 1. HLV calculation: (Income - Expenses) * (Retirement - Age) + Liabilities - Savings
    # (12L - 3L) * (60 - 30) + 20L - 5L = 9L * 30 + 15L = 270L + 15L = 285L (₹2.85 Crore)
    hlv = calculate_hlv(
        age=30,
        retirement_age=60,
        annual_income=1200000.0,
        personal_expenses=300000.0,
        liabilities=2000000.0,
        savings=500000.0
    )
    assert hlv == 28500000.0

    # Negative bounds test (HLV shouldn't go below 0)
    hlv_neg = calculate_hlv(30, 60, 10000, 20000, 0, 1000000)
    assert hlv_neg == 0.0

    # 2. Health Cover suggestions
    # Individual Tier 1
    assert recommend_health_cover("Individual", "1", False) == 500000.0
    # Couple Tier 2
    assert recommend_health_cover("Couple", "2", False) == 500000.0
    # Family Tier 1 with pre-existing condition (+30%)
    assert recommend_health_cover("Family_1Kid", "1", True) == 1300000.0  # 10L * 1.3


def test_insurance_routing():
    """Verify multi-agent routing for insurance queries."""
    assert route_query("should I buy term insurance or ULIP?") == "INSURANCE"
    assert route_query("what health insurance plan is best for family floaters?") == "INSURANCE"
    assert route_query("my policy premium is due") == "INSURANCE"


def test_insurance_page(client):
    """Verify GET /insurance serves the planning dashboard."""
    res = client.get("/insurance")
    assert res.status_code == 200
    assert b"Insurance" in res.data


def test_policy_crud(client):
    """Verify policy management API endpoints."""
    # 1. Get policies (initially empty)
    res = client.get("/api/insurance/policies")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert len(data["policies"]) == 0

    # 2. Add policy (POST)
    payload = {
        "policy_name": "My Term Life Insurance",
        "policy_type": "life",
        "provider": "Max Life",
        "sum_insured": 10000000.0,
        "premium_amount": 15000.0,
        "premium_frequency": "annual",
        "expiry_date": "2055-12-31"
    }
    res = client.post("/api/insurance/policies", json=payload)
    assert res.status_code == 201
    data = json.loads(res.data)
    assert data["status"] == "success"
    assert data["policy"]["policy_name"] == "My Term Life Insurance"
    policy_id = data["policy"]["id"]

    # 3. Verify in database
    with app.app_context():
        policy = InsurancePolicy.query.get(policy_id)
        assert policy is not None
        assert policy.provider == "Max Life"
        assert policy.sum_insured == 10000000.0

    # 4. Edit policy (PUT)
    update_payload = {
        "policy_name": "My Updated Term Life Insurance",
        "premium_amount": 14000.0
    }
    res = client.put(f"/api/insurance/policies/{policy_id}", json=update_payload)
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["status"] == "success"
    assert data["policy"]["policy_name"] == "My Updated Term Life Insurance"
    assert data["policy"]["premium_amount"] == 14000.0

    # 5. Delete policy (DELETE)
    res = client.delete(f"/api/insurance/policies/{policy_id}")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["status"] == "success"

    # Verify deleted in database
    with app.app_context():
        policy = InsurancePolicy.query.get(policy_id)
        assert policy is None


def test_needs_analysis_workflow(client):
    """Verify that submitting needs analysis generates ideal targets and measures gaps."""
    # 1. Log a Life and a Health policy first to measure gaps later
    client.post("/api/insurance/policies", json={
        "policy_name": "Basic Life Policy",
        "policy_type": "life",
        "provider": "LIC",
        "sum_insured": 5000000.0,  # 50 Lakhs cover
        "premium_amount": 20000.0,
        "premium_frequency": "annual"
    })
    client.post("/api/insurance/policies", json={
        "policy_name": "Standard Health Plan",
        "policy_type": "health",
        "provider": "Star Health",
        "sum_insured": 300000.0,  # 3 Lakhs cover
        "premium_amount": 8000.0,
        "premium_frequency": "annual"
    })

    # 2. Run needs analysis calculation
    payload = {
        "age": 30,
        "retirement_age": 60,
        "annual_income": 1200000.0,
        "personal_expenses": 300000.0,
        "liabilities": 2000000.0,
        "savings": 500000.0,
        "family_size": "Family_1Kid",  # Ideal health cover base: Tier 1 -> 10L
        "tier": "1",
        "pre_existing": False
    }
    
    res = client.post("/api/insurance/recommendation", json=payload)
    assert res.status_code == 200
    data = json.loads(res.data)
    
    assert data["status"] == "success"
    rec = data["recommendation"]
    
    # Recommended Life (HLV) should be: (12L - 3L)*30 + 20L - 5L = 285L (₹2.85 Crore)
    assert rec["recommended_life"] == 28500000.0
    # Existing Life was ₹50 Lakhs
    assert rec["existing_life"] == 5000000.0
    # Life Gap should be: 285L - 50L = 235L (₹2.35 Crore)
    assert rec["life_gap"] == 23500000.0
    
    # Recommended Health should be 10 Lakhs (Family_1Kid in Tier 1 Metro)
    assert rec["recommended_health"] == 1000000.0
    # Existing Health was ₹3 Lakhs
    assert rec["existing_health"] == 300000.0
    # Health Gap should be: 10L - 3L = 7 Lakhs
    assert rec["health_gap"] == 700000.0
    
    # 3. Retrieve recommendation and verify GET endpoint calculates correct gaps
    get_res = client.get("/api/insurance/recommendation")
    assert get_res.status_code == 200
    get_data = json.loads(get_res.data)
    
    saved_rec = get_data["recommendation"]
    assert saved_rec is not None
    assert saved_rec["recommended_life"] == 28500000.0
    assert saved_rec["life_gap"] == 23500000.0
    assert saved_rec["health_gap"] == 700000.0

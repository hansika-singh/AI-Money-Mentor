import sys
from unittest.mock import MagicMock, patch

# Mock out external libraries
sys.modules['yfinance'] = MagicMock()
sys.modules['groq'] = MagicMock()
sys.modules['pdfplumber'] = MagicMock()

import pytest
from app import app, db
from models import User

@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            
            # Create a test user
            user = User(username="testuser", email="test@example.com", password_hash="pbkdf2:sha256:260000$test")
            db.session.add(user)
            db.session.commit()
            user_id = user.id
            
            # Log in user via session
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user_id)
                sess['_fresh'] = True
                
            yield client
            
            db.session.remove()
            db.drop_all()

class TestExplainabilityAPI:
    def test_tax_explainability_offline(self, client):
        # Force Groq client to None (offline mode)
        with patch('app.client', None):
            res = client.post('/tax', json={
                "income": 1200000,
                "deduction_80c": 150000,
                "deduction_80d": 25000,
                "deduction_hra": 50000
            })
            assert res.status_code == 200
            data = res.get_json()["tax"]
            
            assert "explainability" in data
            exp = data["explainability"]
            assert "assumptions" in exp
            assert len(exp["assumptions"]) > 0
            assert "top_drivers" in exp
            assert len(exp["top_drivers"]) > 0
            assert "lever_contributions" in exp
            assert exp["lever_contributions"]["80c"] > 0
            assert exp["lever_contributions"]["80d"] > 0
            assert exp["lever_contributions"]["hra"] > 0
            assert "recommendations" in exp
            assert len(exp["recommendations"]) > 0

    def test_tax_simulate_explainability(self, client):
        res = client.post('/tax/simulate', json={
            "income": 1500000,
            "scenario_a": {
                "deduction_80c": 100000,
                "deduction_80d": 15000,
                "deduction_hra": 30000
            },
            "scenario_b": {
                "deduction_80c": 150000,
                "deduction_80d": 25000,
                "deduction_hra": 60000
            }
        })
        assert res.status_code == 200
        data = res.get_json()["result"]
        
        assert "explainability" in data
        exp = data["explainability"]
        assert "assumptions" in exp
        assert "top_drivers" in exp
        assert "lever_contributions" in exp
        
        levers = exp["lever_contributions"]
        assert "scenario_a" in levers
        assert "scenario_b" in levers
        assert levers["scenario_a"]["80c"] > 0
        assert levers["scenario_b"]["80c"] >= levers["scenario_a"]["80c"]

    def test_sip_explainability(self, client):
        res = client.post('/sip', json={
            "monthly": 10000,
            "rate": 12.0,
            "years": 10,
            "inflation": 6.0
        })
        assert res.status_code == 200
        data = res.get_json()
        
        assert "explainability" in data
        exp = data["explainability"]
        assert "inputs" in exp
        assert exp["inputs"]["monthly_investment"] == 10000
        assert exp["inputs"]["expected_return_rate"] == 12.0
        assert exp["inputs"]["duration_years"] == 10
        assert exp["inputs"]["inflation_rate"] == 6.0
        
        assert "formulas" in exp
        assert "nominal_future_value" in exp["formulas"]
        assert "inflation_adjusted_value" in exp["formulas"]
        
        assert "sensitivity" in exp
        sens = exp["sensitivity"]
        assert "rate_plus_1_percent" in sens
        assert "rate_minus_1_percent" in sens
        assert "inflation_plus_1_percent" in sens
        assert "inflation_minus_1_percent" in sens
        
        # Test direction of differences
        assert sens["rate_plus_1_percent"]["difference"] > 0
        assert sens["rate_minus_1_percent"]["difference"] < 0
        assert sens["inflation_plus_1_percent"]["difference"] < 0
        assert sens["inflation_minus_1_percent"]["difference"] > 0

    def test_goal_planner_explainability(self, client):
        res = client.post('/goal-planner', json={
            "goal": 1000000,
            "rate": 12.0,
            "years": 10
        })
        assert res.status_code == 200
        data = res.get_json()
        
        assert "explainability" in data
        exp = data["explainability"]
        assert "inputs" in exp
        assert exp["inputs"]["target_goal"] == 1000000
        assert exp["inputs"]["expected_return_rate"] == 12.0
        assert exp["inputs"]["duration_years"] == 10
        
        assert "formulas" in exp
        assert "required_monthly_sip" in exp["formulas"]
        
        assert "sensitivity" in exp
        sens = exp["sensitivity"]
        assert "rate_plus_1_percent" in sens
        assert "rate_minus_1_percent" in sens
        assert "duration_plus_1_year" in sens
        assert "duration_minus_1_year" in sens
        
        # Increasing return rate or duration should lower the required monthly SIP
        # So rate_plus_1_percent diff should be negative, duration_plus_1_year diff should be negative
        assert sens["rate_plus_1_percent"]["difference"] < 0
        assert sens["rate_minus_1_percent"]["difference"] > 0
        assert sens["duration_plus_1_year"]["difference"] < 0
        assert sens["duration_minus_1_year"]["difference"] > 0

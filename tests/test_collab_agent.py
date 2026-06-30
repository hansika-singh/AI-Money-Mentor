import pytest
import json
from unittest.mock import MagicMock
from app import app
import app as app_module

@pytest.fixture
def collab_client():
    """Test client with a mocked Groq client that simulates sequential agent execution."""
    original_client = app_module.client

    mock_client = MagicMock()
    
    # Mock planning step response (JSON list of agents)
    mock_planning_choice = MagicMock()
    mock_planning_choice.message.content = json.dumps([
        {"agent_key": "investment", "sub_task": "Calculate house down payment savings.", "timeline_point": "Save Down Payment"},
        {"agent_key": "tax", "sub_task": "Calculate house tax benefits.", "timeline_point": "Tax Planning"}
    ])
    mock_planning_response = MagicMock()
    mock_planning_response.choices = [mock_planning_choice]

    # Mock agent execution step responses
    mock_agent_choice = MagicMock()
    mock_agent_choice.message.content = "Mocked Agent response."
    mock_agent_response = MagicMock()
    mock_agent_response.choices = [mock_agent_choice]

    # Mock synthesis step response
    mock_synthesis_choice = MagicMock()
    mock_synthesis_choice.message.content = "Mocked Synthesized final plan."
    mock_synthesis_response = MagicMock()
    mock_synthesis_response.choices = [mock_synthesis_choice]

    # Set side effect to handle planning call, agent calls, and synthesis call
    mock_client.chat.completions.create.side_effect = [
        mock_planning_response,   # 1st call: ChiefPlanner planning
        mock_agent_response,      # 2nd call: InvestmentAgent
        mock_agent_response,      # 3rd call: TaxAgent
        mock_synthesis_response   # 4th call: Synthesized response
    ]

    app_module.client = mock_client
    app.config["TESTING"] = True

    with app.test_client() as client:
        yield client, mock_client

    app_module.client = original_client


def test_collab_agent_success(collab_client):
    """Verify that the collaborative multi-agent routes and executes sequentially."""
    client, mock_client = collab_client
    res = client.post("/agent", json={"query": "Help me buy a house in 5 years"})
    
    assert res.status_code == 200
    data = res.get_json()
    
    assert data["success"] is True
    assert "Mocked Synthesized final plan" in data["response"]
    assert len(data["plan_steps"]) == 2
    
    assert data["plan_steps"][0]["agent_name"] == "Investment Agent"
    assert data["plan_steps"][0]["timeline_point"] == "Save Down Payment"
    assert data["plan_steps"][1]["agent_name"] == "Tax Agent"
    assert data["plan_steps"][1]["timeline_point"] == "Tax Planning"

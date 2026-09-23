import json
from pathlib import Path

from fastapi.testclient import TestClient

from src.api import app
from src.extract import extract_goal
from src.validators import validate_goal


ROOT = Path(__file__).resolve().parents[1]

def test_extract_goal_and_validate():
    payload = json.loads((ROOT / "samples" / "siis_responses.json").read_text())
    item = payload["responses"][0]
    goal = extract_goal(item["original_query"], item["siis_response"])
    assert validate_goal(goal)
    assert goal.goal.startswith("Follow these steps to")
    assert goal.title
    assert goal.actions


def test_health_and_troubleshoot_endpoint():
    client = TestClient(app)
    health = client.get("/health")
    assert health.status_code == 200

    payload = json.loads((ROOT / "samples" / "siis_responses.json").read_text())
    item = payload["responses"][0]
    response = client.post("/v1/troubleshoot", json={"query": item["original_query"], "siis_response": item["siis_response"]})
    assert response.status_code == 200
    body = response.json()
    assert "response" in body
    assert "contexts" in body["response"]


def test_no_match_fallback():
    client = TestClient(app)
    response = client.post("/v1/troubleshoot", json={"query": "totally unrelated mythic device thing", "siis_response": None})
    assert response.status_code == 200
    body = response.json()
    assert body["response"]["contexts"] == [] or body["fallback"] == "no_match"

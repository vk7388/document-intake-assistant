import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient

from main import app
from state import reset_state

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset():
    reset_state()
    yield
    reset_state()


def test_home_endpoint():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "running" in resp.json()["message"]


def test_message_flow_updates_state_and_asks_next_question():
    resp = client.post("/api/message", json={"message": "My name is Rahul Sharma"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["state"]["full_name"] == "Rahul Sharma"
    assert "address" in data["reply"].lower()


def test_document_endpoint_reflects_state():
    client.post("/api/message", json={"message": "My name is Rahul Sharma"})
    resp = client.get("/api/document")
    assert "Rahul Sharma" in resp.json()["document"]


def test_reset_endpoint_clears_state():
    client.post("/api/message", json={"message": "My name is Rahul Sharma"})
    client.post("/api/reset")
    resp = client.get("/api/state")
    assert resp.json()["full_name"] is None

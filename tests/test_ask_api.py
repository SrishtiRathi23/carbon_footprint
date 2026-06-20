"""Tests for the follow-up assistant endpoint (Gemini mocked)."""

import pytest
from fastapi.testclient import TestClient

import app as app_module
from routes import ask as ask_module


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(
        ask_module, "answer_followup", lambda q, ctx: f"answer to: {q}"
    )
    return TestClient(app_module.app)


def test_ask_returns_answer(client):
    response = client.post(
        "/api/ask",
        json={"question": "Why is cycling greener?", "context": {"options": []}},
    )
    assert response.status_code == 200
    assert response.json()["answer"] == "answer to: Why is cycling greener?"


def test_ask_rejects_empty_question(client):
    response = client.post("/api/ask", json={"question": "   ", "context": {}})
    assert response.status_code == 400


def test_ask_rejects_overlong_question(client):
    response = client.post(
        "/api/ask", json={"question": "x" * 600, "context": {}}
    )
    assert response.status_code == 400

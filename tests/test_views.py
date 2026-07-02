import json
from unittest.mock import patch

import pytest

CHAT_URL = "/api/v1/chat/"
PAYLOAD = {
    "message": "Hello",
    "conversation_id": "test-001",
    "message_history": [],
}


@pytest.mark.django_db
def test_chat_manual_mode(client):
    # Mock the LLM call so CI doesn't need a real Groq API call
    with patch("api.views.llm_client.generate_response_with_fallback", return_value="Hi there!"):
        response = client.post(
            CHAT_URL,
            data=json.dumps(PAYLOAD),
            content_type="application/json",
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["response"] == "Hi there!"
    assert data["mode"] == "manual"


@pytest.mark.django_db
def test_chat_agentic_mode(client):
    agentic_payload = {**PAYLOAD, "use_agentic": True}

    with patch(
        "api.views.agent.dispatch",
        return_value=("Answer from agent", "search_web", "test query"),
    ):
        response = client.post(
            CHAT_URL,
            data=json.dumps(agentic_payload),
            content_type="application/json",
        )

    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "agentic"
    assert data["tool_used"] == "search_web"
    assert data["query_used"] == "test query"


@pytest.mark.django_db
def test_chat_missing_message(client):
    response = client.post(
        CHAT_URL,
        data=json.dumps({}),
        content_type="application/json",
    )
    # Empty message still goes through — LLM handles it
    assert response.status_code in (200, 400)


@pytest.mark.django_db
def test_chat_invalid_json(client):
    response = client.post(
        CHAT_URL,
        data="not json",
        content_type="application/json",
    )
    assert response.status_code == 400

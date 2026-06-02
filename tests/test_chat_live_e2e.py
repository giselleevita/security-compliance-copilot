import os

import pytest
from dotenv import dotenv_values
from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.integration
def test_chat_live_end_to_end_with_real_dependencies() -> None:
    env_values = dotenv_values(".env")
    provider = (os.getenv("LLM_PROVIDER") or env_values.get("LLM_PROVIDER") or "gemini").lower()
    required_key = "GROQ_API_KEY" if provider == "groq" else "GEMINI_API_KEY"
    if not (os.getenv(required_key) or env_values.get(required_key)):
        pytest.skip(f"{required_key} is not set.")

    client = TestClient(app)
    health = client.get("/health")
    if health.status_code != 200:
        pytest.skip("Health endpoint unavailable for live test.")
    indexed = int(health.json().get("indexed_chunks", 0))
    if indexed <= 0:
        pytest.skip("No indexed corpus found; run ingestion first.")

    headers = {}
    chat_api_key = os.getenv("CHAT_API_KEY") or env_values.get("CHAT_API_KEY")
    if chat_api_key:
        headers["x-api-key"] = chat_api_key
    response = client.post(
        "/chat",
        headers=headers,
        json={"question": "What does NIST AI RMF recommend for governance roles and accountability?"},
    )
    if response.status_code == 503:
        pytest.skip("Live LLM provider is temporarily unavailable or rate limited.")
    assert response.status_code == 200
    payload = response.json()

    assert isinstance(payload.get("answer"), str)
    assert payload.get("answer", "").strip()
    assert payload.get("guardrail_status") in {"ok", "insufficient_context", "refused"}
    assert payload.get("confidence") in {"high", "medium", "low"}
    assert isinstance(payload.get("sources"), list)

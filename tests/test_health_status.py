from fastapi.testclient import TestClient

from app.main import app


def test_health_status_shape() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] in {"ok", "degraded"}
    assert payload["indexed_chunks"] >= 0
    assert isinstance(payload["known_sources"], list)
    assert "last_ingest_at" in payload


def test_readiness_endpoint_reports_not_ready_without_required_runtime_config() -> None:
    client = TestClient(app)
    response = client.get("/ready")

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["status"] == "not_ready"
    assert "llm_provider_supported" in detail["checks"]
    assert "llm_api_key_configured" in detail["checks"]
    assert "index_populated" in detail["checks"]


def test_readiness_endpoint_returns_ready_payload_when_all_checks_pass(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.health.get_readiness_status",
        lambda: {
            "status": "ready",
            "ready": True,
            "llm_provider": "groq",
            "checks": {
                "llm_provider_supported": True,
                "llm_api_key_configured": True,
                "chat_api_key_configured": True,
                "ingest_api_key_configured": True,
                "index_populated": True,
                "vector_store_healthy": True,
            },
            "health": {"status": "ok", "indexed_chunks": 1},
        },
    )
    client = TestClient(app)

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json()["ready"] is True

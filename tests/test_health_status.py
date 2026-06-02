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

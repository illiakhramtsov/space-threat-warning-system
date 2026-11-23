"""MVP business logic, EDA async signal ingestion, and Lab 3 500 error masking tests."""

from fastapi.testclient import TestClient

from app.core.config import get_settings
from tests.conftest import auth_header


def test_mvp_radar_and_threat_workflow(client: TestClient, seeded_users: dict) -> None:
    """Verify radar registration, threat scoring, EDA ingestion, and admin verification."""
    alice_headers = auth_header(client, "operator_alice", "AlicePass123!")
    admin_headers = auth_header(client, "cmd_admin", "AdminPass123!")

    # 1. Operator registers a radar station
    radar_resp = client.post(
        "/api/v1/radars",
        json={"code": "RAD-UA-01", "name": "Carpathian Deep Space", "region": "West"},
        headers=alice_headers,
    )
    assert radar_resp.status_code == 201
    radar_id = radar_resp.json()["id"]

    # 2. Operator creates a critical threat (< 50,000 km)
    threat_resp = client.post(
        "/api/v1/threats",
        json={
            "object_code": "AST-99942-APOPHIS",
            "threat_type": "asteroid",
            "distance_km": 31000.0,
            "velocity_kms": 42.0,
            "radar_station_id": radar_id,
            "description": "Close Earth approach",
        },
        headers=alice_headers,
    )
    assert threat_resp.status_code == 201
    assert threat_resp.json()["severity"] == "critical"
    threat_id = threat_resp.json()["id"]

    # 3. Async EDA signal ingestion returns 202 Accepted + server_id
    ingest_resp = client.post(
        "/api/v1/signals/ingest",
        json={
            "object_code": "DEBRIS-LEO-441",
            "threat_type": "space_debris",
            "distance_km": 120000.0,
            "velocity_kms": 18.2,
            "radar_station_id": radar_id,
        },
        headers=alice_headers,
    )
    assert ingest_resp.status_code == 202
    assert ingest_resp.json()["status"] == "accepted"
    assert "X-Server-ID" in ingest_resp.headers

    # 4. Admin verifies and broadcasts planetary alert
    verify_resp = client.patch(
        f"/api/v1/admin/threats/{threat_id}/status",
        json={"status": "alert_broadcasted"},
        headers=admin_headers,
    )
    assert verify_resp.status_code == 200
    assert verify_resp.json()["status"] == "alert_broadcasted"


def test_production_hides_stacktrace_on_500(client: TestClient, monkeypatch) -> None:
    """Lab 3: Ensure 500 errors hide internal tracebacks when DEBUG=False."""
    settings = get_settings()
    monkeypatch.setattr(settings, "DEBUG", False)

    resp = client.get("/api/v1/system/simulate-error")
    assert resp.status_code == 500
    body = resp.json()
    assert body["detail"] == "Internal Server Error"
    assert "debug_error" not in body
    assert "Traceback" not in resp.text

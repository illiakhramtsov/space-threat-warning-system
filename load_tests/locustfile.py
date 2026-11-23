"""Lab 4 & Lab 6: Locust load test simulating radar bursts and operator traffic."""

import random
import uuid

from locust import HttpUser, between, task


class SpaceThreatUser(HttpUser):
    """Simulates radar stations streaming telemetry and operators querying threats."""

    wait_time = between(0.2, 1.0)
    token: str | None = None

    def on_start(self) -> None:
        """Register and authenticate a unique virtual operator/radar agent."""
        uid = uuid.uuid4().hex[:10]
        username = f"radar_{uid}"
        password = "LoadTestPassword2026!"
        email = f"{username}@radar-net.org"

        self.client.post(
            "/api/v1/auth/register",
            json={
                "username": username,
                "email": email,
                "password": password,
                "full_name": f"Virtual Radar {uid}",
            },
            name="/api/v1/auth/register",
        )
        resp = self.client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": password},
            name="/api/v1/auth/login",
        )
        if resp.status_code == 200:
            self.token = resp.json().get("access_token")

    @property
    def _headers(self) -> dict[str, str]:
        if not self.token:
            return {}
        return {"Authorization": f"Bearer {self.token}"}

    @task(2)
    def check_root_and_health(self) -> None:
        self.client.get("/", name="GET /")
        self.client.get("/health", name="GET /health")

    @task(3)
    def list_active_threats(self) -> None:
        self.client.get(
            "/api/v1/threats?limit=25",
            headers=self._headers,
            name="GET /api/v1/threats",
        )

    @task(5)
    def ingest_async_radar_signal(self) -> None:
        """Primary EDA workload: high-frequency asynchronous radar signal bursts."""
        payload = {
            "object_code": f"OBJ-{random.randint(1000, 99999)}",
            "threat_type": random.choice(["asteroid", "space_debris", "solar_flare", "unknown"]),
            "distance_km": round(random.uniform(15_000.0, 1_500_000.0), 2),
            "velocity_kms": round(random.uniform(5.0, 55.0), 2),
            "azimuth": round(random.uniform(0.0, 360.0), 1),
            "elevation": round(random.uniform(-45.0, 90.0), 1),
            "description": "Automated peak burst radar telemetry",
        }
        self.client.post(
            "/api/v1/signals/ingest",
            json=payload,
            headers=self._headers,
            name="POST /api/v1/signals/ingest",
        )

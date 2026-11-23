"""Unit & integration tests for Lab 2: Auth, Vertical RBAC, and Horizontal IDOR."""

from fastapi.testclient import TestClient

from tests.conftest import auth_header


def test_anonymous_access_returns_401(client: TestClient) -> None:
    """Scenario 1: Anonymous requests to protected endpoints must return 401."""
    protected_routes = [
        "/api/v1/auth/me",
        "/home/user",
        "/home/admin",
        "/api/v1/threats",
        "/api/v1/admin/overview",
    ]
    for route in protected_routes:
        response = client.get(route)
        assert response.status_code == 401, f"Expected 401 on {route}"


def test_registration_and_login_success_and_failure(client: TestClient) -> None:
    """Scenario 2: Valid credentials return 200; invalid credentials return 401."""
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "username": "new_operator",
            "email": "new_op@radar-net.org",
            "password": "StrongPassword99!",
            "full_name": "New Operator",
        },
    )
    assert reg.status_code == 201
    assert reg.json()["role"] == "user"

    # Successful login -> 200 OK
    login_ok = client.post(
        "/api/v1/auth/login",
        json={"username": "new_operator", "password": "StrongPassword99!"},
    )
    assert login_ok.status_code == 200
    assert "access_token" in login_ok.json()

    # Wrong password -> 401 Unauthorized
    login_bad_pass = client.post(
        "/api/v1/auth/login",
        json={"username": "new_operator", "password": "WrongPassword!"},
    )
    assert login_bad_pass.status_code == 401

    # Unknown user -> 401 Unauthorized
    login_unknown = client.post(
        "/api/v1/auth/login",
        json={"username": "ghost_user", "password": "StrongPassword99!"},
    )
    assert login_unknown.status_code == 401


def test_vertical_privilege_escalation_returns_403(client: TestClient, seeded_users: dict) -> None:
    """Scenario 3: Regular user attempting to access admin endpoints gets 403."""
    alice_headers = auth_header(client, "operator_alice", "AlicePass123!")
    admin_headers = auth_header(client, "cmd_admin", "AdminPass123!")

    # Regular user can open user home page
    assert client.get("/home/user", headers=alice_headers).status_code == 200

    # Regular user is blocked from admin home page & admin API
    assert client.get("/home/admin", headers=alice_headers).status_code == 403
    assert client.get("/api/v1/admin/overview", headers=alice_headers).status_code == 403
    assert client.get("/api/v1/admin/users", headers=alice_headers).status_code == 403

    # Admin succeeds on admin routes
    assert client.get("/home/admin", headers=admin_headers).status_code == 200
    assert client.get("/api/v1/admin/overview", headers=admin_headers).status_code == 200


def test_horizontal_idor_profile_and_threat_returns_403(
    client: TestClient, seeded_users: dict
) -> None:
    """Scenario 4 (IDOR): User A cannot modify User B's profile or threat entity."""
    alice_headers = auth_header(client, "operator_alice", "AlicePass123!")
    bob_headers = auth_header(client, "operator_bob", "BobPass123!")
    bob_id = seeded_users["bob"].id

    # Alice tries to read or update Bob's profile -> 403 Forbidden
    resp_get_bob = client.get(f"/api/v1/users/{bob_id}", headers=alice_headers)
    assert resp_get_bob.status_code == 403

    resp_patch_bob = client.patch(
        f"/api/v1/users/{bob_id}",
        json={"full_name": "Hacked Name"},
        headers=alice_headers,
    )
    assert resp_patch_bob.status_code == 403

    # Bob creates a cosmic threat signal
    create_resp = client.post(
        "/api/v1/threats",
        json={
            "object_code": "NEO-2026-XR7",
            "threat_type": "asteroid",
            "distance_km": 42000.0,
            "velocity_kms": 31.5,
            "description": "Detected by Bob's orbital radar",
        },
        headers=bob_headers,
    )
    assert create_resp.status_code == 201
    threat_id = create_resp.json()["id"]

    # Alice tries to modify or delete Bob's threat signal -> 403 Forbidden
    idor_patch = client.patch(
        f"/api/v1/threats/{threat_id}",
        json={"description": "Tampered by Alice"},
        headers=alice_headers,
    )
    assert idor_patch.status_code == 403

    idor_delete = client.delete(f"/api/v1/threats/{threat_id}", headers=alice_headers)
    assert idor_delete.status_code == 403

    # Bob (owner) can modify his own threat -> 200 OK
    owner_patch = client.patch(
        f"/api/v1/threats/{threat_id}",
        json={"description": "Updated trajectory confirmed"},
        headers=bob_headers,
    )
    assert owner_patch.status_code == 200

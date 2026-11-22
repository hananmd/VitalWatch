from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_needs_no_auth(client: TestClient) -> None:
    response = client.get("/health", headers={"Authorization": ""})

    assert response.status_code == 200

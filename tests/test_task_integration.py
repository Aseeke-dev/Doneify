from fastapi.testclient import TestClient

from conftest import FakeRedis


def test_authenticated_user_can_create_read_update_and_delete_task(
    client: TestClient,
    fake_redis: FakeRedis,
) -> None:
    email = "task-owner@example.com"
    password = "correct-password"

    register_response = client.post(
        "/api/v1/auth/register",
        json={"username": "Task Owner", "email": email, "password": password},
    )
    assert register_response.status_code == 200

    verification_response = client.post(
        "/api/v1/auth/verify-account",
        json={"email": email, "code": fake_redis.values[f"otp:{email}"]},
    )
    assert verification_response.status_code == 200

    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert login_response.status_code == 200
    csrf_headers = {"X-CSRF-Token": login_response.json()["csrf_token"]}

    create_response = client.post(
        "/api/v1/tasks",
        headers=csrf_headers,
        json={"title": "First task", "description": "Task details"},
    )
    assert create_response.status_code == 201
    created_task = create_response.json()
    task_id = created_task["id"]
    assert created_task["title"] == "First task"
    assert created_task["completed"] is False

    list_response = client.get("/api/v1/tasks")
    assert list_response.status_code == 200
    assert [task["id"] for task in list_response.json()] == [task_id]

    get_response = client.get(f"/api/v1/tasks/{task_id}")
    assert get_response.status_code == 200
    assert get_response.json()["title"] == "First task"

    update_response = client.put(
        f"/api/v1/tasks/{task_id}",
        headers=csrf_headers,
        json={
            "title": "Updated task",
            "description": "Updated details",
            "completed": True,
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Updated task"
    assert update_response.json()["completed"] is True

    delete_response = client.delete(
        f"/api/v1/tasks/{task_id}", headers=csrf_headers
    )
    assert delete_response.status_code == 204

    missing_response = client.get(f"/api/v1/tasks/{task_id}")
    assert missing_response.status_code == 404
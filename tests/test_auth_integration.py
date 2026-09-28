from fastapi.testclient import TestClient

from conftest import FakeRedis


def test_register_stores_otp_and_sends_verification_email(
    client: TestClient,
    fake_redis: FakeRedis,
    sent_emails: list[tuple[str, str]],
) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "Test User",
            "email": "register@example.com",
            "password": "correct-password",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "Message": "Login Successful. check your mail for verification code"
    }
    assert sent_emails[0][0] == "register@example.com"
    assert fake_redis.values["otp:register@example.com"] == sent_emails[0][1]


def test_register_then_verify_then_login_and_read_profile(
    client: TestClient,
    fake_redis: FakeRedis,
) -> None:
    email = "workflow@example.com"
    password = "correct-password"

    register_response = client.post(
        "/api/v1/auth/register",
        json={"username": "Workflow User", "email": email, "password": password},
    )
    assert register_response.status_code == 200

    code = fake_redis.values[f"otp:{email}"]
    verify_response = client.post(
        "/api/v1/auth/verify-account",
        json={"email": email, "code": code},
    )
    assert verify_response.status_code == 200
    assert verify_response.json()["Message"] == "Email verified successfully. Kindly login to your account"

    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert login_response.status_code == 200
    assert "access_token" in login_response.cookies
    assert "refresh_token" in login_response.cookies
    assert "csrf_token" in login_response.cookies

    profile_response = client.get("/api/v1/auth/me")
    assert profile_response.status_code == 200
    assert profile_response.json()["email"] == email
    assert profile_response.json()["username"] == "Workflow User"


def test_login_rejects_unverified_user(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "Unverified User",
            "email": "unverified@example.com",
            "password": "correct-password",
        },
    )
    assert response.status_code == 200

    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": "unverified@example.com", "password": "correct-password"},
    )

    assert login_response.status_code == 400
    assert login_response.json()["detail"] == "Email not verified. Kindly verify your email"
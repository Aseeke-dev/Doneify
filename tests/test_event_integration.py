import asyncio
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from conftest import FakeRedis
from app.services.event_reminders import process_due_event_reminders


class FakeEventMailer:
    def __init__(self, fail_first_send: bool = False) -> None:
        self.attempts: list[tuple[str, str, datetime]] = []
        self.fail_first_send = fail_first_send

    async def send_event_reminder(
        self, email: str, event_title: str, starts_at: datetime
    ) -> None:
        self.attempts.append((email, event_title, starts_at))
        if self.fail_first_send:
            self.fail_first_send = False
            raise RuntimeError("Simulated SMTP failure")


def test_event_reminder_retries_and_is_sent_only_once(
    client: TestClient,
    fake_redis: FakeRedis,
    db_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    email = "event-owner@example.com"
    password = "correct-password"
    now = datetime.now(timezone.utc)

    register_response = client.post(
        "/api/v1/auth/register",
        json={"username": "Event Owner", "email": email, "password": password},
    )
    assert register_response.status_code == 202
    verify_response = client.post(
        "/api/v1/auth/verify-account",
        json={"email": email, "code": fake_redis.values[f"otp:{email}"]},
    )
    assert verify_response.status_code == 200
    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert login_response.status_code == 200
    csrf_headers = {"X-CSRF-Token": login_response.json()["csrf_token"]}

    invalid_reminder_response = client.post(
        "/api/v1/events",
        headers=csrf_headers,
        json={
            "title": "Invalid reminder",
            "starts_at": (now + timedelta(hours=2)).isoformat(),
            "reminder_minutes": 15,
        },
    )
    assert invalid_reminder_response.status_code == 422

    naive_time_response = client.post(
        "/api/v1/events",
        headers=csrf_headers,
        json={
            "title": "Missing timezone",
            "starts_at": (now + timedelta(hours=2)).replace(tzinfo=None).isoformat(),
            "reminder_minutes": 30,
        },
    )
    assert naive_time_response.status_code == 422

    create_response = client.post(
        "/api/v1/events",
        headers=csrf_headers,
        json={
            "title": "Planning session",
            "description": "Quarterly planning",
            "starts_at": (now + timedelta(minutes=40)).isoformat(),
            "reminder_minutes": 30,
        },
    )
    assert create_response.status_code == 201, create_response.text
    created_event = create_response.json()
    event_id = created_event["id"]
    assert create_response.headers["location"] == f"/api/v1/events/{event_id}"
    assert created_event["reminder_minutes"] == 30

    list_response = client.get("/api/v1/events")
    assert list_response.status_code == 200
    assert [event["id"] for event in list_response.json()] == [event_id]

    mailer = FakeEventMailer(fail_first_send=True)
    assert asyncio.run(
        process_due_event_reminders(db_session_factory, mailer, now)
    ) == 0
    assert not mailer.attempts

    reminder_due_at = now + timedelta(minutes=10)
    assert asyncio.run(
        process_due_event_reminders(db_session_factory, mailer, reminder_due_at)
    ) == 0
    assert asyncio.run(
        process_due_event_reminders(db_session_factory, mailer, reminder_due_at)
    ) == 1
    assert asyncio.run(
        process_due_event_reminders(db_session_factory, mailer, reminder_due_at)
    ) == 0
    assert len(mailer.attempts) == 2
    assert mailer.attempts[0][0] == email

    update_response = client.patch(
        f"/api/v1/events/{event_id}",
        headers=csrf_headers,
        json={
            "title": "Updated planning session",
            "starts_at": (now + timedelta(hours=2)).isoformat(),
            "reminder_minutes": 60,
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Updated planning session"
    assert update_response.json()["reminder_sent_at"] is None

    delete_response = client.delete(
        f"/api/v1/events/{event_id}",
        headers=csrf_headers,
    )
    assert delete_response.status_code == 204
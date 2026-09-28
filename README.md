# Doneify

Doneify is a FastAPI backend for Managing tasks and events. Event reminders are sent to the event owner's email at the selected
lead time. The API is versioned under `/api/v1` and uses PostgreSQL, Redis,
SQLAlchemy, and Alembic.

## Features

- Account registration, email verification, login, logout, and token refresh.
- Password-reset requests with privacy-preserving responses.
- User-scoped task and event CRUD APIs.
- Event reminders 30 minutes, 1 hour, or 24 hours before the event.
- Cookie-based authentication with CSRF protection on state-changing requests.
- Alembic migrations applied automatically when the Compose API starts.

## Requirements

- Docker Engine with Docker Compose v2.
- OpenSSL for generating local secrets.
- `uv` if you want to run tests outside Docker.
- SMTP credentials to send verification and event reminder emails.
- Google OAuth credentials only if using Google sign-in.

## First-Time Setup

Copy the example configuration:

```bash
cp .env.example .env
```

Generate two separate values:

```bash
openssl rand -hex 24
openssl rand -hex 32
```

Put the first value in `.env` as `POSTGRES_PASSWORD` and the second as
`SECRET_KEY`. Hexadecimal passwords are URL-safe because Compose uses the
database password in `DATABASE_URL`. Fill in `MAIL_USERNAME` and `MAIL_PASSWORD`
to enable email delivery. Google OAuth values are optional unless you use that
flow.

Never commit `.env`. It contains local credentials and is excluded from the
Docker build context.

## Run With Docker Compose

Build and start the API, PostgreSQL, and Redis:

```bash
docker compose up -d --build
docker compose ps
```

Compose waits for PostgreSQL and Redis health checks, applies the migrations,
then starts the API. PostgreSQL and Redis are reachable only on the internal
Compose network; only the API port is published on the host.

- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>

Stop the services while retaining database and Redis data:

```bash
docker compose down
```

The named volumes persist between runs. `docker compose down -v` deletes those
volumes and all data stored in them; use it only when intentionally resetting
the local database.

## API Routes

All routes below are prefixed with `/api/v1`.

| Resource | Method and path | Behavior |
| --- | --- | --- |
| Register | `POST /auth/register` | Start registration and email verification; returns `202 Accepted`. |
| Verify account | `POST /auth/verify-account` | Verify with the emailed four-digit code. |
| Resend verification | `POST /auth/resend-verification` | Request another verification code. |
| Login | `POST /auth/login` | Form fields `username` (email) and `password`; sets auth cookies. |
| Current user | `GET /auth/me` | Return the authenticated user's profile. |
| Logout | `POST /auth/logout` | Revoke the refresh token and clear auth cookies. |
| Refresh | `POST /auth/refresh` | Refresh the access token. |
| Request password reset | `POST /auth/password-reset-requests` | JSON body with `email`; response does not disclose account existence. |
| Confirm password reset | `POST /auth/password-reset-confirmations` | JSON body with email, reset token, and new password. |
| Google sign-in | `GET /auth/google/login`, `GET /auth/google/callback` | Start and complete OAuth sign-in. |
| Tasks | `GET`, `POST /tasks` | List the user's tasks or create a task. |
| Task item | `GET`, `PATCH`, `DELETE /tasks/{task_id}` | Read, partially update, or delete an owned task. |
| Events | `GET`, `POST /events` | List the user's events or create an event. |
| Event item | `GET`, `PATCH`, `DELETE /events/{event_id}` | Read, partially update, or delete an owned event. |

Authenticated writes to tasks and events, logout, and token refresh require the
`X-CSRF-Token` header matching the `csrf_token` cookie. Task/event resources are
scoped to the authenticated user. Creates return `201 Created` and a `Location`
header; deletes return `204 No Content`.

### Create an Event

`starts_at` must be an ISO 8601 timestamp with a timezone. The reminder offset
must be `30`, `60`, or `1440` minutes.

```json
{
  "title": "Project review",
  "description": "Review the next release",
  "starts_at": "2030-01-15T14:30:00Z",
  "reminder_minutes": 60
}
```

The application polls for due reminders every 30 seconds. SMTP failures are
logged and retried on a later poll. Delivery is at-least-once: a process crash
after an SMTP server accepts an email but before the database records delivery
can result in a duplicate reminder.

## Migrations

Compose runs migrations before starting the API. To run Alembic commands inside
the API container:

```bash
docker compose exec api alembic current
docker compose exec api alembic heads
docker compose exec api alembic upgrade head
```

Every ORM schema change should include an Alembic migration. Alembic discovers
models registered with the shared metadata in `app/core/base.py`; new models
must be imported by the migrations environment.

## Tests

The test suite uses an isolated SQLite database plus in-memory Redis and email
fakes; it does not require the Compose services to run.

```bash
uv sync --locked --group dev
uv run pytest -q
```

## Troubleshooting

**Compose says `POSTGRES_PASSWORD` is missing:** copy `.env.example` to `.env`
and set a generated password before starting the stack.

**A password change does not work with an existing database volume:** the
PostgreSQL image only applies `POSTGRES_PASSWORD` when initializing an empty
data directory. Change the role password in the existing database to match
`.env`:

```bash
docker compose exec db psql -U postgres -d Doneify
```

At the `psql` prompt run `\password postgres`, enter the new password, then exit
with `\q`. Run `docker compose up -d` afterward. This preserves the existing
volume.

**Email is not delivered:** check `MAIL_USERNAME` and `MAIL_PASSWORD`. The API
can start without working SMTP credentials, but verification and event email
delivery will fail until they are configured correctly.

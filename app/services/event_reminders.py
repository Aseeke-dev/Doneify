import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import selectinload

from ..api.dependencies import EmailService
from ..core.database import SessionLocal
from ..models.event import Event

logger = logging.getLogger(__name__)
POLL_INTERVAL_SECONDS = 30


def _due_conditions(now: datetime):
    return and_(
        Event.reminder_sent_at.is_(None),
        Event.starts_at > now,
        or_(
            and_(
                Event.reminder_minutes == 30,
                Event.starts_at <= now + timedelta(minutes=30),
            ),
            and_(
                Event.reminder_minutes == 60,
                Event.starts_at <= now + timedelta(minutes=60),
            ),
            and_(
                Event.reminder_minutes == 1440,
                Event.starts_at <= now + timedelta(minutes=1440),
            ),
        ),
    )


async def process_due_event_reminders(
    session_factory: async_sessionmaker = SessionLocal,
    email_service: EmailService | None = None,
    now: datetime | None = None,
) -> int:
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None or current_time.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    current_time = current_time.astimezone(timezone.utc)
    mailer = email_service or EmailService()

    async with session_factory() as session:
        result = await session.execute(
            select(Event.id)
            .where(_due_conditions(current_time))
            .order_by(Event.starts_at)
        )
        event_ids = result.scalars().all()

    sent_count = 0
    for event_id in event_ids:
        async with session_factory() as session:
            result = await session.execute(
                select(Event)
                .options(selectinload(Event.user))
                .where(Event.id == event_id, _due_conditions(current_time))
                .with_for_update(skip_locked=True)
            )
            event = result.scalar_one_or_none()
            if event is None:
                continue

            try:
                await mailer.send_event_reminder(
                    event.user.email,
                    event.title,
                    event.starts_at,
                )
            except Exception:
                await session.rollback()
                logger.exception("Failed to send reminder for event %s", event_id)
                continue

            event.reminder_sent_at = current_time
            await session.commit()
            sent_count += 1

    return sent_count


async def event_reminder_worker(
    process_reminders: Callable[[], Awaitable[int]] = process_due_event_reminders,
) -> None:
    while True:
        try:
            await process_reminders()
        except Exception:
            logger.exception("Event reminder polling failed")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
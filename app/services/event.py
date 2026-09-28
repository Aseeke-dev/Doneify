from datetime import datetime, timezone

from fastapi import HTTPException, status

from ..models.event import Event
from ..repositories.event import EventRepository
from ..schemas.event import EventCreate, EventUpdate


class EventService:
    def __init__(self, db) -> None:
        self.events = EventRepository(db)

    async def create(self, user_id: int, data: EventCreate) -> Event:
        event = Event(
            title=data.title,
            description=data.description,
            starts_at=data.starts_at.astimezone(timezone.utc),
            reminder_minutes=data.reminder_minutes,
            user_id=user_id,
        )
        return await self.events.create(event)

    async def get_all(self, user_id: int):
        return await self.events.get_all(user_id)

    async def get(self, event_id: int, user_id: int) -> Event:
        event = await self.events.get_by_id(event_id, user_id)
        if event is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
        return event

    async def update(self, event_id: int, user_id: int, data: EventUpdate) -> Event:
        event = await self.get(event_id, user_id)
        changes = data.model_dump(exclude_unset=True)

        if "starts_at" in changes:
            starts_at = changes["starts_at"]
            if starts_at is None or starts_at.tzinfo is None or starts_at.utcoffset() is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="starts_at must include a timezone",
                )
            starts_at = starts_at.astimezone(timezone.utc)
            if starts_at <= datetime.now(timezone.utc):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="starts_at must be in the future",
                )
            changes["starts_at"] = starts_at

        reminder_changed = "starts_at" in changes or "reminder_minutes" in changes
        for field, value in changes.items():
            setattr(event, field, value)
        if reminder_changed:
            event.reminder_sent_at = None
        return await self.events.save(event)

    async def delete(self, event_id: int, user_id: int) -> None:
        event = await self.get(event_id, user_id)
        await self.events.delete(event)
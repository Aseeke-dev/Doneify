from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.event import Event


class EventRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, event_id: int, user_id: int) -> Event | None:
        result = await self.db.execute(
            select(Event).where(Event.id == event_id, Event.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, user_id: int) -> Sequence[Event]:
        result = await self.db.execute(
            select(Event)
            .where(Event.user_id == user_id)
            .order_by(Event.starts_at)
        )
        return result.scalars().all()

    async def create(self, event: Event) -> Event:
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def save(self, event: Event) -> Event:
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def delete(self, event: Event) -> None:
        await self.db.delete(event)
        await self.db.commit()
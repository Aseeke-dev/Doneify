from collections.abc import Sequence
from typing import cast

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.auth import User
from ....models.event import Event
from ....schemas.event import EventCreate, EventResponse, EventUpdate
from ....services.event import EventService
from ...dependencies import get_current_user, require_csrf_token

router = APIRouter(prefix="/events", tags=["Events"])


@router.post(
    "",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf_token)],
)
async def create_event(
    data: EventCreate,
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Event:
    event = await EventService(db).create(cast(int, current_user.id), data)
    response.headers["Location"] = f"/api/v1/events/{event.id}"
    return event


@router.get("", response_model=list[EventResponse])
async def get_events(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Sequence[Event]:
    return await EventService(db).get_all(cast(int, current_user.id))


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Event:
    return await EventService(db).get(event_id, cast(int, current_user.id))


@router.patch(
    "/{event_id}",
    response_model=EventResponse,
    dependencies=[Depends(require_csrf_token)],
)
async def update_event(
    event_id: int,
    data: EventUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Event:
    return await EventService(db).update(
        event_id, cast(int, current_user.id), data
    )


@router.delete(
    "/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf_token)],
)
async def delete_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    await EventService(db).delete(event_id, cast(int, current_user.id))
import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.services.event_reminders import event_reminder_worker


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
	worker = asyncio.create_task(event_reminder_worker())
	try:
		yield
	finally:
		worker.cancel()
		try:
			await worker
		except asyncio.CancelledError:
			pass


app = FastAPI(title="Doneify API", version="1.0.0", lifespan=lifespan)

app.include_router(api_router, prefix="/api/v1")
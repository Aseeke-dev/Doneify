from fastapi import APIRouter
from .endpoints.auth import router as auth_router
from .endpoints.task import router as task_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(task_router)
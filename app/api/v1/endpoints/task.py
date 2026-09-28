from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from collections.abc import Sequence
from typing import cast

from ....core.database import get_db
from ....models.auth import User
from ....models.task import Task
from ....schemas.task import TaskCreate, TaskResponse, TaskUpdate
from ....services.task import TaskService
from ...dependencies import get_current_user, require_csrf_token

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post(
	"",
	response_model=TaskResponse,
	status_code=status.HTTP_201_CREATED,
	dependencies=[Depends(require_csrf_token)],
)
async def create_task(
	task: TaskCreate,
	db: AsyncSession = Depends(get_db),
	current_user: User = Depends(get_current_user),
) -> TaskResponse:
	return await TaskService(db).create_task(cast(int, current_user.id), task)


@router.get("", response_model=list[TaskResponse])
async def get_all_tasks(
	db: AsyncSession = Depends(get_db),
	current_user: User = Depends(get_current_user),
) -> Sequence[Task]:
	return await TaskService(db).get_all_tasks(cast(int, current_user.id))


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
	task_id: int,
	db: AsyncSession = Depends(get_db),
	current_user: User = Depends(get_current_user),
) -> TaskResponse:
	task = await TaskService(db).get_task_by_id(
		task_id, cast(int, current_user.id)
	)
	if task is None:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="Task not found",
		)
	return task


@router.put(
	"/{task_id}",
	response_model=TaskResponse,
	dependencies=[Depends(require_csrf_token)],
)
async def update_task(
	task_id: int,
	task: TaskUpdate,
	db: AsyncSession = Depends(get_db),
	current_user: User = Depends(get_current_user),
) -> TaskResponse:
	updated_task = await TaskService(db).update_task(
		task_id, cast(int, current_user.id), task
	)
	if updated_task is None:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="Task not found",
		)
	return updated_task


@router.delete(
	"/{task_id}",
	status_code=status.HTTP_204_NO_CONTENT,
	dependencies=[Depends(require_csrf_token)],
)
async def delete_task(
	task_id: int,
	db: AsyncSession = Depends(get_db),
	current_user: User = Depends(get_current_user),
) -> Response:
	deleted = await TaskService(db).delete_task(
		task_id, cast(int, current_user.id)
	)
	if not deleted:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="Task not found",
		)
	return Response(status_code=status.HTTP_204_NO_CONTENT)
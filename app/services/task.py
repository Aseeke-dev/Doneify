from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.task import TaskRepo
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse
from collections.abc import Sequence

class TaskService:
    def __init__(self, db: AsyncSession) -> None:
        self.taskrepo = TaskRepo(db)
    
    async def get_task_by_id(self, task_id: int, user_id: int) -> Task | None:
        return await self.taskrepo.get_task_by_id(task_id, user_id)
    
    async def get_all_tasks(self, user_id: int) -> Sequence[Task]:
        return await self.taskrepo.get_all_tasks(user_id)
    
    async def create_task(self, user_id: int, task: TaskCreate) -> TaskResponse:
        new_task = Task(
            title=task.title,
            description=task.description,
            user_id=user_id,
            completed=False,
        )
        created_task = await self.taskrepo.create_task(new_task)
        return TaskResponse.model_validate(created_task)
    
    async def update_task(self, task_id: int, user_id: int, updated_task: TaskUpdate) -> TaskResponse | None:
        changes = updated_task.model_dump(exclude_unset=True)
        task = await self.taskrepo.update_task(task_id, user_id, changes)
        return TaskResponse.model_validate(task) if task else None
    
    async def delete_task(self, task_id: int, user_id: int) -> bool:
        return await self.taskrepo.delete_task(task_id, user_id)
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.task import TaskRepo
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse

class TaskService:
    def __init__(self, db: AsyncSession) -> None:
        self.taskrepo = TaskRepo(db)
    
    async def get_task_by_id(self, id: int, user_id: int) -> Task:
        return await self.taskrepo.get_task_by_id(id, user_id)
    
    async def get_all_tasks(self, user_id: int):
        return await self.taskrepo.get_all_tasks(user_id)
    
    async def create_task(self, user_id: int, task: TaskCreate) -> TaskResponse:
        new_task = Task(
            title=task.title,
            description=task.description,
            user_id=user_id,
            completed=False,
        )
        created_task = await self.taskrepo.create_task(new_task)
        return TaskResponse.from_orm(created_task)
    
    async def update_task(self, task_id: int, user_id: int, updated_task: TaskUpdate) -> TaskResponse | None:
        existing_task = await self.taskrepo.get_task_by_id(task_id, user_id)
        if not existing_task:
            return None
        
        if updated_task.title is not None:
            existing_task.title = updated_task.title
        if updated_task.description is not None:
            existing_task.description = updated_task.description
        if updated_task.completed is not None:
            existing_task.completed = updated_task.completed
        
        updated_task = await self.taskrepo.update_task(task_id, user_id, existing_task)
        return TaskResponse.from_orm(updated_task) if updated_task else None
    
    async def delete_task(self, task_id: int, user_id: int) -> bool:
        return await self.taskrepo.delete_task(task_id, user_id)
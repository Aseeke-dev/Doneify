from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task


class TaskRepo:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = db
        
    async def get_task_by_id(self, task_id: int, user_id: int) -> Task | None:
        query = select(Task).where(Task.id == task_id, Task.user_id == user_id)
        result = await self.repo.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all_tasks(self, user_id: int) -> Sequence[Task]:
        query = select(Task).where(Task.user_id == user_id).order_by(Task.id)
        result = await self.repo.execute(query)
        return result.scalars().all()
    
    async def create_task(self, task: Task) -> Task:
        self.repo.add(task)
        await self.repo.commit()
        await self.repo.refresh(task)
        
        return task
    
    async def update_task(
        self, task_id: int, user_id: int, changes: dict[str, object]
    ) -> Task | None:
        task = await self.get_task_by_id(task_id, user_id)
        if not task:
            return None
        for key, value in changes.items():
            setattr(task, key, value)
        await self.repo.commit()
        await self.repo.refresh(task)
        return task
    
    async def delete_task(self, task_id: int, user_id: int) -> bool:
        task = await self.get_task_by_id(task_id, user_id)
        if not task:
            return False
        await self.repo.delete(task)
        await self.repo.commit()
        return True
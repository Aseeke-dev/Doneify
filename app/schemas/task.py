from pydantic import BaseModel
from datetime import datetime

class TaskBase(BaseModel):
    title: str
    description: str | None = None

class TaskCreate(TaskBase):
    pass

class TaskUpdate(TaskBase):
    completed: bool | None = None
    
class TaskResponse(TaskBase):
    id: int
    completed: bool
    created_at: datetime
    user_id: int

    model_config = {"from_attributes": True}
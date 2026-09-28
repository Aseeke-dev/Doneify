from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

class TaskBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1024)

class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1024)
    completed: bool | None = None

    @field_validator("title", "completed")
    @classmethod
    def reject_null_required_values(cls, value):
        if value is None:
            raise ValueError("This field cannot be null")
        return value

    @model_validator(mode="after")
    def require_update_fields(self) -> TaskUpdate:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class TaskResponse(TaskBase):
    id: int
    completed: bool
    created_at: datetime
    user_id: int

    model_config = ConfigDict(from_attributes=True)
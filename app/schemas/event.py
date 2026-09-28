from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ReminderMinutes = Literal[30, 60, 1440]


class EventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1024)
    starts_at: datetime
    reminder_minutes: ReminderMinutes

    @field_validator("starts_at")
    @classmethod
    def validate_starts_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("starts_at must include a timezone")
        value = value.astimezone(timezone.utc)
        if value <= datetime.now(timezone.utc):
            raise ValueError("starts_at must be in the future")
        return value


class EventUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1024)
    starts_at: datetime | None = None
    reminder_minutes: ReminderMinutes | None = None

    @field_validator("title", "starts_at", "reminder_minutes")
    @classmethod
    def validate_required_updates(cls, value):
        if value is None:
            raise ValueError("This field cannot be null")
        return value

    @model_validator(mode="after")
    def require_an_update(self) -> EventUpdate:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class EventResponse(BaseModel):
    id: int
    title: str
    description: str | None
    starts_at: datetime
    reminder_minutes: int
    reminder_sent_at: datetime | None
    user_id: int

    model_config = ConfigDict(from_attributes=True)
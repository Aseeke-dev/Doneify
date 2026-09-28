from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.base import Base

if TYPE_CHECKING:
    from .auth import User


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint(
            "reminder_minutes IN (30, 60, 1440)",
            name="ck_events_reminder_minutes",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reminder_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    reminder_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user: Mapped[User] = relationship("User", back_populates="events")
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from ..core.base import Base
from sqlalchemy.orm import relationship
from datetime import datetime
from .task import Task
from .event import Event

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    refresh_token = relationship("RefreshToken", back_populates="user")
    tasks = relationship("Task", back_populates="user")
    events = relationship("Event", back_populates="user", cascade="all, delete-orphan")

class RefreshToken(Base):
    __tablename__ = "refresh_token"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String, nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    user = relationship("User", back_populates='refresh_token')

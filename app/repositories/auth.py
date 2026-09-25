from sqlalchemy.ext.asyncio import AsyncSession
from ..models.auth import User
from sqlalchemy import select

class AuthRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = db

    async def get_user_by_email(self, email: str):
        query = select(User).where(User.email==email)
        result= await self.repo.execute(query)
        return result.scalar_one_or_none()

    async def create_user(self, user: User) -> User:
        self.repo.add(user)
        await self.repo.commit()
        await self.repo.refresh(user)
        return user
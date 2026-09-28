from sqlalchemy.ext.asyncio import AsyncSession
from ..models.auth import User, RefreshToken
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

    async def verify_user(self, email: str):
        user = await self.get_user_by_email(email)

        if user:
            user.is_verified = True  # pyright: ignore[reportAttributeAccessIssue]
            await self.repo.commit()
            await self.repo.refresh(user)

    async def save_token(self, token: str, user_email: str):
        user = await self.get_user_by_email(user_email)
        if user:
            new_token = RefreshToken(user_id=user.id, token=token)
            self.repo.add(new_token)
            await self.repo.commit()
            await self.repo.refresh(new_token)

    async def get_refresh_token(self, token: str):
        query = select(RefreshToken).where(
            RefreshToken.token == token,
            RefreshToken.revoked.is_(False),
        )
        result = await self.repo.execute(query)
        return result.scalar_one_or_none()

    async def revoke_refresh_token(self, token: str) -> None:
        stored_token = await self.get_refresh_token(token)
        if stored_token:
            stored_token.revoked = True # pyright: ignore[reportAttributeAccessIssue]
            await self.repo.commit()

    async def reset_user_password(self, email: str, new_hashed_password: str):
        user = await self.get_user_by_email(email)
        if user:
            user.password = new_hashed_password  # pyright: ignore[reportAttributeAccessIssue]
            await self.repo.commit()
            await self.repo.refresh(user)
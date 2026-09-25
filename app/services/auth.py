from ..repositories.auth import AuthRepository
from ..core.config import Settings
from fastapi import Response, HTTPException, status
from ..schemas.auth import UserCreate, UserResponse
from ..models.auth import User
from ..core.security import hash_password

settings = Settings() # pyright: ignore[reportCallIssue]

class AuthService:
    def __init__(self, db) -> None:
        self.authrepo = AuthRepository(db)

    def _secure_cookie(self) -> bool:
        return settings.ENVIRONMENT != "development" and settings.SECURE_COOKIES

    def _set_cookie(self, response: Response, name: str, value: str, max_age: int) -> None:
        response.set_cookie(
            name,
            value,
            max_age=max_age,
            httponly=True,
            secure=self._secure_cookie(),
            samesite="lax",
            path="/"
        )

    def _clear_cookie(self, response: Response, name: str) -> None:
        response.delete_cookie(
            name,
            path="/",
            secure=self._secure_cookie(),
            samesite="lax",
            httponly=True
        )

    async def create_user(self, data: UserCreate):
        existing_user = await self.authrepo.get_user_by_email(data.email)

        if existing_user:
            HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists. Kindly sign in"
            )

        data.password = hash_password(data.password)
        new_user = User(**data.model_dump())
        await self.authrepo.create_user(new_user)
        

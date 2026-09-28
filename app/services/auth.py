from ..repositories.auth import AuthRepository
from ..core.config import Settings
from fastapi import (
    Response,
    HTTPException,
    status,
    BackgroundTasks,
    Request
    )
from ..schemas.auth import UserCreate, UserResponse, VerifyAccountSubmit
from ..models.auth import User
from ..core.security import (
    hash_password,
    generate_4_digit_code,
    verify_password,
    create_access_token,
    create_refresh_token,
    generate_csrf_token,
    create_reset_token
    )
from ..api.dependencies import redis_client, EmailService
import httpx
import jwt
settings = Settings() # pyright: ignore[reportCallIssue]
OTP_MAX_ATTEMPTS = 5
OTP_TTL_SECONDS = 300
OTP_RESEND_LIMIT = 3
OTP_RESEND_WINDOW_SECONDS = 3600
OTP_RESEND_COOLDOWN_SECONDS = 60

class AuthService:
    def __init__(self, db) -> None:
        self.authrepo = AuthRepository(db)
        self.mail = EmailService()

    def _secure_cookie(self) -> bool:
        return settings.ENVIRONMENT != "development" and settings.SECURE_COOKIES

    def _set_cookie(self, response: Response, name: str, value: str, max_age: int) -> None:
        response.set_cookie(
            name,
            value,
            max_age=max_age,
            httponly=name != "csrf_token",
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

    async def create_user(self, data: UserCreate, background_task: BackgroundTasks):
        existing_user = await self.authrepo.get_user_by_email(data.email)

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already exists. Kindly sign in"
            )

        user_data = data.model_dump()
        user_data["password"] = hash_password(data.password)
        new_user = User(**user_data)
        await self.authrepo.create_user(new_user)

        otp = generate_4_digit_code()
        redis_client.setex(f"otp:{new_user.email}", 300, otp)
        redis_client.delete(f"otp_attempts:{new_user.email}")

        await self.mail.send_otp(data.email, otp, background_task)

        return {"message": "Verification email sent"}

    async def verify_user(self, data: VerifyAccountSubmit):
        redis_key = f"otp:{data.email}"
        attempts_key = f"otp_attempts:{data.email}"
        cached_code = redis_client.get(redis_key)

        if not cached_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail= "Verification error"
            )

        attempts = redis_client.incr(attempts_key)
        if attempts == 1:
            redis_client.expire(attempts_key, OTP_TTL_SECONDS)

        if attempts > OTP_MAX_ATTEMPTS:
            redis_client.delete(redis_key, attempts_key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many verification attempts. Request a new code."
            )

        if cached_code != data.code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification error"
            )

        redis_client.delete(redis_key, attempts_key)
        await self.authrepo.verify_user(data.email)
        return {"message": "Email verified successfully"}

    async def resend_verification_code(
        self, email: str, background_task: BackgroundTasks
    ):
        user = await self.authrepo.get_user_by_email(email)
        if user is None:
            return {"message": "If the account can be verified, a new code has been sent."}

        if getattr(user, "is_verified", False) is True:
            return {"message": "If the account can be verified, a new code has been sent."}

        cooldown_key = f"otp_resend_cooldown:{email}"
        if not redis_client.set(
            cooldown_key, "1", ex=OTP_RESEND_COOLDOWN_SECONDS, nx=True
        ):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Please wait before requesting another verification code.",
            )

        resend_count_key = f"otp_resend_count:{email}"
        resend_count = redis_client.incr(resend_count_key)
        if resend_count == 1:
            redis_client.expire(resend_count_key, OTP_RESEND_WINDOW_SECONDS)
        if resend_count > OTP_RESEND_LIMIT:
            redis_client.delete(cooldown_key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many verification codes requested. Try again later.",
            )

        otp = generate_4_digit_code()
        redis_client.setex(f"otp:{email}", OTP_TTL_SECONDS, otp)
        redis_client.delete(f"otp_attempts:{email}")
        await self.mail.send_otp(email, otp, background_task)
        return {"message": "If the account can be verified, a new code has been sent."}

    async def authenticate_user(self, email: str, password: str):
        user = await self.authrepo.get_user_by_email(email)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        if not verify_password(password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        if user.is_verified is False:  # pyright: ignore[reportAttributeAccessIssue]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email not verified. Kindly verify your email"
            )

        return user

    async def login(self, email: str, password: str, response: Response):
        user = await self.authenticate_user(email, password)

        access_token = create_access_token({"sub": user.email})
        refresh_token = create_refresh_token({"sub": user.email})

        await self.authrepo.save_token(refresh_token, email)

        csrf = generate_csrf_token()

        self._set_cookie(
            response,
            "access_token",
            access_token,
            30 * 60
        )
        self._set_cookie(
            response,
            "refresh_token",
            refresh_token,
            365 * 24 * 60 * 60
        )
        self._set_cookie(
            response,
            "csrf_token",
            csrf,
            30 * 60
        )
        return {"message": "Login successful", "csrf_token": csrf}

    async def google_callback(self, response: Response, code: str):
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code"
        }

        async with httpx.AsyncClient() as client:
            token_response = await client.post(token_url, data=token_data)

        if token_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to obtain access token from Google"
                )
        token_json = token_response.json()
        access_token = token_json.get("access_token")

        userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            userinfo_response = await client.get(userinfo_url, headers=headers)

        if userinfo_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to obtain user info from Google"
                )
        userinfo = userinfo_response.json()
        email = userinfo.get("email")

        user = await self.authrepo.get_user_by_email(email)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User not found. Please sign up first."
            )

        access_token = create_access_token({"sub": user.email})
        refresh_token = create_refresh_token({"sub": user.email})

        await self.authrepo.save_token(refresh_token, email)

        csrf = generate_csrf_token()

        self._set_cookie(
            response,
            "access_token",
            access_token,
            30 * 60
        )
        self._set_cookie(
            response,
            "refresh_token",
            refresh_token,
            365 * 24 * 60 * 60
        )
        self._set_cookie(
            response,
            "csrf_token",
            csrf,
            30 * 60
        )
        return {"message": "Login successful", "csrf_token": csrf}

    async def logout(self, response: Response, request: Request):
        refresh_token = request.cookies.get("refresh_token")
        if refresh_token:
            await self.authrepo.revoke_refresh_token(refresh_token)

        self._clear_cookie(response, "access_token")
        self._clear_cookie(response, "refresh_token")
        self._clear_cookie(response, "csrf_token")

        return {"message": "Logout successful"}

    async def refresh_access_token(self, response: Response, request: Request):
        refresh_token = request.cookies.get("refresh_token")

        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token missing"
            )

        stored_token = await self.authrepo.get_refresh_token(refresh_token)

        if not stored_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        try:
            payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            email = payload.get("sub")
            if not isinstance(email, str) or not email:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token"
                )
        except jwt.PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        new_access_token = create_access_token({"sub": email})
        new_csrf_token = generate_csrf_token()

        self._set_cookie(
            response,
            "access_token",
            new_access_token,
            30 * 60
        )
        self._set_cookie(
            response,
            "csrf_token",
            new_csrf_token,
            30 * 60
        )

        return {"message": "Access token refreshed", "csrf_token": new_csrf_token}

    async def forgot_password(self, email: str, background_task: BackgroundTasks):
        user = await self.authrepo.get_user_by_email(email)

        if not user:
            return {
                "message": "If an account exists, password reset instructions have been sent."
            }

        reset_token = create_reset_token(user.email) # pyright: ignore[reportArgumentType]
        redis_client.setex(f"reset_token:{user.email}", 300, reset_token)

        await self.mail.send_reset_token(email, reset_token, background_task)

        return {
            "message": "If an account exists, password reset instructions have been sent."
        }

    async def reset_password(self, email: str, reset_token: str, new_password: str):
        redis_key = f"reset_token:{email}"
        cached_token = redis_client.get(redis_key)

        if not cached_token or cached_token != reset_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )

        user = await self.authrepo.get_user_by_email(email)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        await self.authrepo.reset_user_password(email, hash_password(new_password))
        redis_client.delete(redis_key)

        return {"message": "Password reset successful"}

    async def get_profile(self, email: str):
        user = await self.authrepo.get_user_by_email(email)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return UserResponse(
            id=user.id, # pyright: ignore[reportArgumentType]
            username=user.username, # pyright: ignore[reportArgumentType]
            email=user.email, # pyright: ignore[reportArgumentType]
        )
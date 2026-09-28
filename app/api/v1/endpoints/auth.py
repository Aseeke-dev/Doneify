import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, BackgroundTasks, Response, Request, HTTPException, status
from fastapi.responses import RedirectResponse
from ....repositories.auth import AuthRepository
from ....services.auth import AuthService
from ....schemas.auth import (
    PasswordResetRequest,
    PasswordResetSubmit,
    ResendVerificationSubmit,
    UserCreate,
    UserResponse,
    VerifyAccountSubmit,
)
from ....core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from ...dependencies import get_current_user, redis_client, require_csrf_token
from ....core.config import Settings
from ....models.auth import User
from typing import Annotated
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(prefix="/auth", tags=["Authentication"])

settings = Settings()  # pyright: ignore[reportCallIssue]

@router.post("/register", status_code=status.HTTP_202_ACCEPTED)
async def register_user(
    user_create: UserCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    auth_service = AuthService(db)
    return await auth_service.create_user(user_create, background_tasks)

@router.post("/verify-account")
async def verify_account(
    verify_account_submit: VerifyAccountSubmit,
    db: AsyncSession = Depends(get_db),
):
    auth_service = AuthService(db)
    return await auth_service.verify_user(verify_account_submit)

@router.post("/resend-verification")
async def resend_verification(
    resend_request: ResendVerificationSubmit,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    auth_service = AuthService(db)
    return await auth_service.resend_verification_code(
        resend_request.email, background_tasks
    )

@router.post("/login")
async def login_user(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    auth_service = AuthService(db)
    return await auth_service.login(form_data.username, form_data.password, response)

@router.get("/google/login")
async def google_login():
    state = secrets.token_urlsafe(32)
    redis_client.setex(f"oauth_state:{state}", 600, "1")
    query = urlencode(
        {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
        }
    )
    response = RedirectResponse(
        f"https://accounts.google.com/o/oauth2/v2/auth?{query}"
    )
    response.set_cookie(
        "google_oauth_state",
        state,
        max_age=600,
        httponly=True,
        secure=settings.ENVIRONMENT != "development" and settings.SECURE_COOKIES,
        samesite="lax",
        path="/",
    )

    return response

@router.get("/google/callback")
async def google_callback(
    code: str,
    state: str,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    expected_state = request.cookies.get("google_oauth_state")
    response.delete_cookie(
        "google_oauth_state",
        secure=settings.ENVIRONMENT != "development" and settings.SECURE_COOKIES,
        httponly=True,
        samesite="lax",
        path="/",
    )
    if (
        not expected_state
        or not secrets.compare_digest(expected_state, state)
        or redis_client.getdel(f"oauth_state:{state}") is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth state",
        )

    auth_service = AuthService(db)
    return await auth_service.google_callback(response, code)

@router.post("/logout", dependencies=[Depends(require_csrf_token)])
async def logout_user(
    response: Response,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    auth_service = AuthService(db)
    return await auth_service.logout(response, request)

@router.post('/refresh', dependencies=[Depends(require_csrf_token)])
async def refresh_token(
    response: Response,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    auth_service = AuthService(db)
    return await auth_service.refresh_access_token(response, request)

@router.post(
    "/password-reset-requests", status_code=status.HTTP_202_ACCEPTED
)
async def forget_password(
    reset_request: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    auth_service = AuthService(db)
    return await auth_service.forgot_password(
        str(reset_request.email), background_tasks
    )

@router.post(
    "/password-reset-confirmations",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def reset_password(
    reset_request: PasswordResetSubmit,
    db: AsyncSession = Depends(get_db),
) -> None:
    auth_service = AuthService(db)
    await auth_service.reset_password(
        reset_request.email,
        reset_request.reset_token,
        reset_request.new_password,
    )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    return current_user
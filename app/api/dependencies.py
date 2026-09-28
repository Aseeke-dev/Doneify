import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request, Depends, HTTPException, Header, status
from ..core.database import get_db
from ..repositories.auth import AuthRepository
from ..models.auth import User
import jwt
import secrets

from fastapi import BackgroundTasks

from ..core.config import Settings
import redis


settings = Settings()  # pyright: ignore[reportCallIssue]

redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True, retry_on_timeout=True)


def require_csrf_token(
    request: Request,
    header_token: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> None:
    cookie_token = request.cookies.get("csrf_token")
    if (
        not cookie_token
        or not header_token
        or not secrets.compare_digest(cookie_token, header_token)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing or invalid",
        )

class EmailService:
    def __init__(self) -> None:
        pass

    def _execute_smtp_send(self, email: str, subject: str, html_content: str) -> None:
        msg = MIMEMultipart()
        msg["From"] = settings.MAIL_USERNAME
        msg["To"] = email
        msg["Subject"] = subject

        msg.attach(MIMEText(html_content, "html"))

        try:
            smtp_host = getattr(settings, "MAIL_SERVER", "smtp.gmail.com")
            smtp_port = getattr(settings, "MAIL_PORT", 587)

            with smtplib.SMTP(host=smtp_host, port=smtp_port) as server:
                server.starttls()
                server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
                server.send_message(msg)
        except Exception as e:
            print(f"SMTP Email Send Error: {e}")

    async def send_otp(
        self, email: str, code: str, background_tasks: BackgroundTasks
    ) -> None:
        subject = "Verify Your Account - Doneify"
        html_content = f"""
        <html>
        <body>
            <h2>Welcome to Doneify!</h2>
            <p>Thank you for registering. Please use the following 4-digit code to verify your account:</p>
            <h1 style="font-size: 32px; letter-spacing: 5px; color: #4CAF50;">{code}</h1>
            <p>This code will expire in 5 minutes.</p>
        </body>
        </html>
        """

        # Enqueue the blocking SMTP call to run asynchronously in the background
        background_tasks.add_task(
            self._execute_smtp_send,
            email=email,
            subject=subject,
            html_content=html_content,
        )

    async def send_reset_token(
        self, email: str, reset_token: str, background_tasks: BackgroundTasks
    ) -> None:
        subject = "Reset Your Password - Doneify"
        html_content = f"""\
<html>
  <body>
    <h2>Reset Your Password</h2>
    <p>You have requested to reset your password. Below is your reset token:</p>
    <h1 style="font-size: 32px; letter-spacing: 5px; color: #4CAF50;">{reset_token}</h1>
    <p>If you did not request this, please ignore this email.</p>
  </body>
</html>
"""

        background_tasks.add_task(
            self._execute_smtp_send,
            email=email,
            subject=subject,
            html_content=html_content,
        )

async def get_current_user(
    request: Request, db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = request.cookies.get("access_token")
    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")  # pyright: ignore[reportAssignmentType]
        if not isinstance(email, str) or not email:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = await AuthRepository(db).get_user_by_email(email)
    if user is None:
        raise credentials_exception
    return user
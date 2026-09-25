import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from fastapi import BackgroundTasks

from ..core.config import Settings

settings = Settings()  # pyright: ignore[reportCallIssue]


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
            <h2>Welcome to NexaMarket!</h2>
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
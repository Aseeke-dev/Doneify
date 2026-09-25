from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    ENVIRONMENT: str = "development"
    SECURE_COOKIES: bool = True
    MAIL_PASSWORD: str
    MAIL_USERNAME: str

    class Config:
        env_file = ".env"
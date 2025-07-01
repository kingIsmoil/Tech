
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    secret_key: str = "qwszfddgfuyt5443frfdhg"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    smtp_server: str = "smtp.example.com"
    smtp_port: int = 587
    smtp_username: str = "ismoilumarzoda"
    smtp_password: str = "slmjrlgwvevkmiqv"
    from_email: str = "ismoilumarzoda@gmail.com"

    class Config:
        env_file = ".env"

settings = Settings()

SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
SMTP_SETTINGS = {
    "server": settings.smtp_server,
    "port": settings.smtp_port,
    "username": settings.smtp_username,
    "password": settings.smtp_password,
    "from_email": settings.from_email
}
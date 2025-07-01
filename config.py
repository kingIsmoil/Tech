
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    secret_key: str = "qwszfddgfuyt5443frfdhg"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 465
    smtp_username: str = "ismoilumarzoda"
    smtp_password: str = "slmjrlgwvevkmiqv"
    from_email: str = "ismoilumarzoda@gmail.com"

    class Config:
        env_file = ".env"
        env_prefix = "" 
        case_sensitive = False  


settings = Settings()

SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
SMTP_SETTINGS = {
    "server": "smtp.gmail.com",
    "port": 465,
    "username": "ismoilumarzoda",
    "password": "slmjrlgwvevkmiqv",
    "from_email":"ismoilumarzoda@gmail.com"
}
print("SMTP SETTINGS:")
print(SMTP_SETTINGS)
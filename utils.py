from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
import smtplib
from typing import Optional
from email.mime.text import MIMEText
from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, SMTP_SETTINGS

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str):
    return pwd_context.hash(password)

def create_verification_token(email: str):
    expire = datetime.utcnow() + timedelta(hours=24)
    payload = {"sub": email, "exp": expire, "type": "verify"}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def send_verification_email(email: str):
    token = create_verification_token(email)
    link = f"http://localhost:8000/verify-email?token={token}"
    message = MIMEText(f"Здравствуйте! Подтвердите ваш email, перейдя по ссылке:\n{link}")
    message["Subject"] = "Подтверждение Email"
    message["From"] = SMTP_SETTINGS["from_email"]
    message["To"] = email

    try:
        with smtplib.SMTP_SSL(SMTP_SETTINGS["server"], SMTP_SETTINGS["port"]) as server:
            server.login(SMTP_SETTINGS["username"], SMTP_SETTINGS["password"])
            server.send_message(message)
        print(f"Verification email sent to {email}")
    except Exception as e:
        print(f"Error sending verification email: {e}")


def send_password_reset_email(email: str, reset_token: str):
    reset_link = f"http://ваш-сайт/reset-password?token={reset_token}"
    message = MIMEText(f"Вы запросили сброс пароля. Перейдите по ссылке: {reset_link}")
    message["Subject"] = "Сброс пароля"
    message["From"] = SMTP_SETTINGS["from_email"]
    message["To"] = email

    try:
        with smtplib.SMTP_SSL(SMTP_SETTINGS["server"], SMTP_SETTINGS["port"]) as server:
            server.login(SMTP_SETTINGS["username"], SMTP_SETTINGS["password"])
            server.send_message(message)
        print(f"Reset email sent to {email}")
    except Exception as e:
        print(f"Error sending reset email: {e}")

def send_booking_confirmation(email: str, date: str, time: str, branch_name: str):
    message_text = f"""
    Подтверждение бронирования:
    
    Филиал: {branch_name}
    Дата: {date}
    Время: {time}
    
    Спасибо за использование нашего сервиса!
    """
    message = MIMEText(message_text)
    message["Subject"] = "Подтверждение бронирования"
    message["From"] = SMTP_SETTINGS["from_email"]
    message["To"] = email

    try:
        with smtplib.SMTP_SSL(SMTP_SETTINGS["server"], SMTP_SETTINGS["port"]) as server:
            server.login(SMTP_SETTINGS["username"], SMTP_SETTINGS["password"])
            server.send_message(message)
        print(f"Booking confirmation sent to {email}")
    except Exception as e:
        print(f"Error sending booking confirmation: {e}")

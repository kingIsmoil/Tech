from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel, EmailStr, validator
from passlib.context import CryptContext

Base = declarative_base()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserRole(str, Enum):
    USER = "user"
    ORGANIZATION = "organization"
    ADMIN = "admin"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    is_verified = Column(Boolean, default=False)
    is_organization = Column(Boolean, default=False)
    role = Column(String, default=UserRole.USER)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    organizations = relationship("Organization", back_populates="owner")
    queue_slots = relationship("QueueSlot", back_populates="user")

    def verify_password(self, plain_password: str):
        return pwd_context.verify(plain_password, self.password)

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    category = Column(String, nullable=False)
    description = Column(String, nullable=True)
    address = Column(String, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="organizations")
    branches = relationship("Branch", back_populates="organization")

class Branch(Base):
    __tablename__ = "branches"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    name = Column(String, nullable=False)
    address = Column(String, nullable=False)
    schedule = Column(JSON, nullable=True)  

    organization = relationship("Organization", back_populates="branches")
    queue_slots = relationship("QueueSlot", back_populates="branch")

class QueueSlotStatus(str, Enum):
    BOOKED = "забронирован"
    CANCELLED = "отменен"
    CONFIRMED = "подтвержден"

class QueueSlot(Base):
    __tablename__ = "queue_slots"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(String, nullable=False)  
    time = Column(String, nullable=False)  
    status = Column(String, default=QueueSlotStatus.BOOKED)
    created_at = Column(DateTime, default=datetime.utcnow)

    branch = relationship("Branch", back_populates="queue_slots")
    user = relationship("User", back_populates="queue_slots")
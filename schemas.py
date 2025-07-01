from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict,Union
from pydantic import BaseModel, EmailStr, validator

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    is_organization: bool = False

class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str]
    is_verified: bool
    is_organization: bool
    role: str  
    created_at: datetime

    class Config:
        orm_mode = True

    class Config:
        orm_mode = True

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class OrganizationCreate(BaseModel):
    name: str
    category: str
    description: Optional[str] = None
    address: Optional[str] = None

class OrganizationOut(BaseModel):
    id: int
    name: str
    category: str
    description: Optional[str]
    address: Optional[str]
    owner_id: int
    created_at: datetime

    class Config:
        orm_mode = True

class BranchCreate(BaseModel):
    organization_id: int
    name: str
    address: str
    schedule: Optional[Dict] = None

class BranchOut(BaseModel):
    id: int
    name: str
    address: str
    schedule: Optional[Dict]

    class Config:
        orm_mode = True

class QueueSlotCreate(BaseModel):
    branch_id: int
    date: str
    time: str

class QueueSlotOut(BaseModel):
    id: int
    branch_id: int
    user_id: int
    date: str
    time: str
    status: str
    created_at: datetime

    class Config:
        orm_mode = True

class OrganizationStats(BaseModel):
    total_branches: int
    active_bookings: int
    cancelled_bookings: int
    confirmed_bookings: int
    popular_branches: List[Dict[str, Union[str, int]]]
    booking_trends: List[Dict[str, Union[str, int]]]

    class Config:
        orm_mode = True

class BranchUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    schedule: Optional[Dict] = None

class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None

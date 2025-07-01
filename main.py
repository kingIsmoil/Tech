from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import JWTError, jwt
from typing import Optional

from models import *
from schemas import *
from database import SessionLocal, engine
from utils import (
    verify_password, 
    get_password_hash,
    create_access_token,
    send_verification_email,
    send_password_reset_email,
    send_booking_confirmation
)
from config import *
Base.metadata.create_all(bind=engine)

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

from fastapi import BackgroundTasks

@app.post("/register", response_model=UserOut)
async def register_user(
    user: UserCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    try:
        db_user = db.query(User).filter(User.email == user.email).first()
        if db_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        hashed_password = get_password_hash(user.password)
        db_user = User(
            email=user.email,
            password=hashed_password,
            full_name=user.full_name,
            is_organization=user.is_organization
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        background_tasks.add_task(send_verification_email, db_user.email)

        return db_user
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Validation error: {str(e)}"
        )


@app.post("/token", response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/forgot-password")
def forgot_password(email: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    reset_token = create_access_token(data={"sub": user.email})
    send_password_reset_email(user.email, reset_token)
    return {"message": "Password reset email sent"}

@app.post("/reset-password")
def reset_password(token: str, new_password: str, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=400, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid token")
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    hashed_password = get_password_hash(new_password)
    user.password = hashed_password
    db.commit()
    return {"message": "Password updated successfully"}

@app.get("/organizations/", response_model=List[OrganizationOut])
def get_organizations(category: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Organization)
    if category:
        query = query.filter(Organization.category == category)
    return query.all()

@app.post("/book-slot/", response_model=QueueSlotOut)
def book_slot(
    slot: QueueSlotCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    branch = db.query(Branch).filter(Branch.id == slot.branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    existing_slot = db.query(QueueSlot).filter(
        QueueSlot.branch_id == slot.branch_id,
        QueueSlot.date == slot.date,
        QueueSlot.time == slot.time,
        QueueSlot.status == QueueSlotStatus.BOOKED
    ).first()
    
    if existing_slot:
        raise HTTPException(status_code=400, detail="This time slot is already booked")
    
    db_slot = QueueSlot(
        branch_id=slot.branch_id,
        user_id=current_user.id,
        date=slot.date,
        time=slot.time,
        status=QueueSlotStatus.BOOKED
    )
    db.add(db_slot)
    db.commit()
    db.refresh(db_slot)
    
    send_booking_confirmation(current_user.email, slot.date, slot.time, branch.name)
    
    return db_slot

@app.post("/organizations/", response_model=OrganizationOut)
def create_organization(
    organization: OrganizationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.is_organization:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must become an organization first (POST /users/become-organization)"
        )
    
    db_org = Organization(
        **organization.dict(),
        owner_id=current_user.id
    )
    db.add(db_org)
    db.commit()
    db.refresh(db_org)
    return db_org

@app.get("/organizations/", response_model=List[OrganizationOut])
def get_organizations(
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    query = db.query(Organization)
    if category:
        query = query.filter(Organization.category == category)
    return query.offset(skip).limit(limit).all()

@app.get("/organizations/{org_id}", response_model=OrganizationOut)
def get_organization(org_id: int, db: Session = Depends(get_db)):
    db_org = db.query(Organization).filter(Organization.id == org_id).first()
    if not db_org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return db_org

@app.put("/organizations/{org_id}", response_model=OrganizationOut)
def update_organization(
    org_id: int,
    org: OrganizationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_org = db.query(Organization).filter(Organization.id == org_id).first()
    if not db_org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    if db_org.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to update this organization")
    
    update_data = org.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_org, field, value)
    
    db.commit()
    db.refresh(db_org)
    return db_org

@app.get("/organizations/{org_id}/branches", response_model=List[BranchOut])
def get_organization_branches(
    org_id: int,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    return db.query(Branch).filter(
        Branch.organization_id == org_id
    ).offset(skip).limit(limit).all()

@app.get("/branches/", response_model=List[BranchOut])
def get_branches(
    organization_id: Optional[int] = None,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    query = db.query(Branch)
    if organization_id:
        query = query.filter(Branch.organization_id == organization_id)
    return query.offset(skip).limit(limit).all()

@app.get("/branches/{branch_id}", response_model=BranchOut)
def get_branch(branch_id: int, db: Session = Depends(get_db)):
    db_branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not db_branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    return db_branch

@app.put("/branches/{branch_id}", response_model=BranchOut)
def update_branch(
    branch_id: int,
    branch: BranchUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not db_branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    
    org = db.query(Organization).filter(
        Organization.id == db_branch.organization_id,
        Organization.owner_id == current_user.id
    ).first()
    if not org:
        raise HTTPException(status_code=403, detail="Not authorized to update this branch")
    
    update_data = branch.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_branch, field, value)
    
    db.commit()
    db.refresh(db_branch)
    return db_branch

@app.delete("/branches/{branch_id}")
def delete_branch(
    branch_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not db_branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    
    org = db.query(Organization).filter(
        Organization.id == db_branch.organization_id,
        Organization.owner_id == current_user.id
    ).first()
    if not org:
        raise HTTPException(status_code=403, detail="Not authorized to delete this branch")
    
    db.delete(db_branch)
    db.commit()
    return {"message": "Branch deleted successfully"}

# main.py (изменение эндпоинта book_slot)
from bot import telegram_notifier

@app.post("/book-slot/", response_model=QueueSlotOut)
async def book_slot(
    slot: QueueSlotCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    branch = db.query(Branch).filter(Branch.id == slot.branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Филиал не найден")
    
    existing_slot = db.query(QueueSlot).filter(
        QueueSlot.branch_id == slot.branch_id,
        QueueSlot.date == slot.date,
        QueueSlot.time == slot.time,
        QueueSlot.status == QueueSlotStatus.BOOKED
    ).first()
    
    if existing_slot:
        raise HTTPException(status_code=400, detail="Это время уже занято")
    
    db_slot = QueueSlot(
        branch_id=slot.branch_id,
        user_id=current_user.id,
        date=slot.date,
        time=slot.time,
        status=QueueSlotStatus.BOOKED
    )
    db.add(db_slot)
    db.commit()
    db.refresh(db_slot)
    
    send_booking_confirmation(current_user.email, slot.date, slot.time, branch.name)
    
    await telegram_notifier.send_booking_notification(db_slot, db)
    
    return db_slot

@app.get("/organizations/{org_id}/stats", response_model=OrganizationStats)
async def get_organization_stats(
    org_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    period: str = "month" 
):
    org = db.query(Organization).filter(
        Organization.id == org_id,
        Organization.owner_id == current_user.id
    ).first()
    
    if not org and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this organization's stats"
        )

    branches = db.query(Branch).filter(
        Branch.organization_id == org_id
    ).all()

    bookings_query = db.query(QueueSlot).join(
        Branch
    ).filter(
        Branch.organization_id == org_id
    )

    if period == "day":
        start_date = datetime.utcnow() - timedelta(days=1)
    elif period == "week":
        start_date = datetime.utcnow() - timedelta(weeks=1)
    elif period == "month":
        start_date = datetime.utcnow() - timedelta(days=30)
    elif period == "year":
        start_date = datetime.utcnow() - timedelta(days=365)
    else:
        start_date = None

    if start_date:
        bookings_query = bookings_query.filter(
            QueueSlot.created_at >= start_date
        )

    all_bookings = bookings_query.all()
    
    stats = {
        "total_branches": len(branches),
        "active_bookings": sum(1 for b in all_bookings if b.status == QueueSlotStatus.BOOKED),
        "cancelled_bookings": sum(1 for b in all_bookings if b.status == QueueSlotStatus.CANCELLED),
        "confirmed_bookings": sum(1 for b in all_bookings if b.status == QueueSlotStatus.CONFIRMED),
        "popular_branches": [],
        "booking_trends": []
    }

    for branch in branches:
        branch_bookings = [b for b in all_bookings if b.branch_id == branch.id]
        stats["popular_branches"].append({
            "branch_name": branch.name,
            "bookings_count": len(branch_bookings)
        })

    if period == "day":
        for hour in range(24):
            hour_start = datetime.utcnow().replace(
                hour=hour, minute=0, second=0, microsecond=0
            ) - timedelta(days=1)
            hour_end = hour_start + timedelta(hours=1)
            count = sum(1 for b in all_bookings if hour_start <= b.created_at < hour_end)
            stats["booking_trends"].append({
                "period": f"{hour:02d}:00",
                "bookings_count": count
            })
    else:
        days = 7 if period == "week" else 30 if period == "month" else 365
        for day in range(days):
            day_start = datetime.utcnow() - timedelta(days=days-day)
            day_end = day_start + timedelta(days=1)
            count = sum(1 for b in all_bookings if day_start <= b.created_at < day_end)
            stats["booking_trends"].append({
                "period": day_start.strftime("%Y-%m-%d"),
                "bookings_count": count
            })

    return stats

@app.get("/organizations/{org_id}/bookings", response_model=List[QueueSlotOut])
async def get_organization_bookings(
    org_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    status: Optional[str] = None,
    branch_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    org = db.query(Organization).filter(
        Organization.id == org_id,
        Organization.owner_id == current_user.id
    ).first()
    
    if not org and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this organization's bookings"
        )

    query = db.query(QueueSlot).join(
        Branch
    ).filter(
        Branch.organization_id == org_id
    )

    if status:
        query = query.filter(QueueSlot.status == status)
    if branch_id:
        query = query.filter(QueueSlot.branch_id == branch_id)
    if start_date:
        query = query.filter(QueueSlot.date >= start_date)
    if end_date:
        query = query.filter(QueueSlot.date <= end_date)

    return query.order_by(QueueSlot.date, QueueSlot.time).all()

@app.post("/users/become-organization", response_model=UserOut)
async def become_organization(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Позволяет обычному пользователю стать организацией
    Требуется повторная авторизация после изменения
    """
    if current_user.is_organization:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already an organization"
        )
    
    current_user.is_organization = True
    current_user.role = UserRole.ORGANIZATION
    db.commit()
    db.refresh(current_user)
    
    return current_user


@app.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "verify":
            raise HTTPException(status_code=400, detail="Invalid token type")
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=400, detail="Invalid token")

        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if user.is_verified:
            return {"message": "Email already verified"}

        user.is_verified = True
        db.commit()
        return {"message": "Email successfully verified!"}

    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

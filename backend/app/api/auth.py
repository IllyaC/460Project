from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..auth_utils import hash_password, verify_password
from ..deps import get_db
from ..models import User
from ..schemas import LoginRequest, RegisterRequest, UserOut

router = APIRouter()


@router.post("/api/auth/register", response_model=UserOut)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    username = payload.username.strip()
    email = payload.email.strip().lower()
    desired_role = payload.desired_role.lower()

    existing = db.execute(
        select(User).where(or_(User.email == email, User.username == username))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Username or email already registered")

    is_approved = desired_role == "student"
    user = User(
        username=username,
        email=email,
        password_hash=hash_password(payload.password),
        role=desired_role,
        is_approved=is_approved,
    )
    db.add(user)
    db.flush()
    db.refresh(user)
    return UserOut.model_validate(user, from_attributes=True)


@router.post("/api/auth/login", response_model=UserOut)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    identifier = payload.username_or_email.strip().lower()
    user = db.execute(
        select(User).where(or_(User.email == identifier, User.username == identifier))
    ).scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return UserOut.model_validate(user, from_attributes=True)

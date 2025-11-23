from typing import Literal

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_session
from .models import ClubMember


class UserContext:
    def __init__(self, email: str, role: Literal["student", "leader", "admin"]):
        self.email = email
        self.role = role


def get_user(
    x_user_email: str = Header(default="student@example.edu"),
    x_user_role: str = Header(default="student"),
) -> UserContext:
    role = x_user_role.lower()
    if role not in {"student", "leader", "admin"}:
        raise HTTPException(status_code=400, detail="X-User-Role must be student, leader, or admin")
    return UserContext(email=x_user_email, role=role)


def get_db():
    with get_session() as session:
        yield session


def ensure_leader(db: Session, club_id: int, user: UserContext) -> None:
    if user.role not in {"leader", "admin"}:
        raise HTTPException(status_code=403, detail="Leader access required")
    if user.role == "admin":
        return
    membership = db.execute(
        select(ClubMember).where(
            ClubMember.club_id == club_id,
            ClubMember.user_email == user.email,
            ClubMember.role == "leader",
            ClubMember.status == "approved",
        )
    ).scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=403, detail="Leader access required for this club")


def ensure_admin(user: UserContext) -> None:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


def ensure_leader_role(user: UserContext) -> None:
    if user.role not in {"leader", "admin"}:
        raise HTTPException(status_code=403, detail="Leader access required")

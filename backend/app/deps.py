from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_session
from .models import ClubMember, User


def get_db():
    with get_session() as session:
        yield session


def get_user(
    x_user_id: int | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not x_user_id and not x_user_email:
        raise HTTPException(status_code=401, detail="User header missing")

    query = select(User)
    if x_user_id:
        query = query.where(User.id == x_user_id)
    elif x_user_email:
        query = query.where(User.email == x_user_email.lower())

    user = db.execute(query).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def ensure_leader(db: Session, club_id: int, user: User) -> None:
    if user.role == "admin":
        return
    if user.role != "leader" or not user.is_approved:
        raise HTTPException(status_code=403, detail="Leader approval required")
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


def ensure_admin(user: User) -> None:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


def ensure_leader_role(user: User) -> None:
    if user.role == "admin":
        return
    if user.role != "leader" or not user.is_approved:
        raise HTTPException(status_code=403, detail="Leader approval required")


def ensure_leader_or_admin(user: User = Depends(get_user)) -> User:
    """Allow only approved leaders or admins.

    Leaders must have been approved by an admin; admins are always allowed.
    """

    if user.role == "admin":
        return user
    if user.role == "leader" and user.is_approved:
        return user
    raise HTTPException(
        status_code=403,
        detail="Only leaders and admins can create events.",
    )

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import ensure_admin, get_db, get_user
from ..models import Club, ClubMember, Flag, User
from ..schemas import ClubSummary, FlagOut, UserOut
from ..services import club_summary, serialize_flag

router = APIRouter()


@router.get("/api/admin/flags", response_model=list[FlagOut])
def list_flags(
    db: Session = Depends(get_db),
    user: User = Depends(get_user),
):
    ensure_admin(user)
    flags = (
        db.execute(
            select(Flag)
            .where(Flag.resolved == False)  # noqa: E712
            .order_by(Flag.created_at.desc())
        )
        .scalars()
        .all()
    )
    return [serialize_flag(flag) for flag in flags]


@router.post("/api/admin/flags/{flag_id}/resolve", response_model=FlagOut)
def resolve_flag(
    flag_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_user),
):
    ensure_admin(user)
    flag = db.get(Flag, flag_id)
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")
    flag.resolved = True
    db.flush()
    db.refresh(flag)
    return serialize_flag(flag)


@router.get("/api/admin/clubs/pending", response_model=list[ClubSummary])
def pending_clubs(
    db: Session = Depends(get_db),
    user: User = Depends(get_user),
):
    ensure_admin(user)
    clubs = (
        db.execute(select(Club).where(Club.approved == False).order_by(Club.name.asc()))  # noqa: E712
        .scalars()
        .all()
    )
    return [club_summary(db, club) for club in clubs]


@router.post("/api/admin/clubs/{club_id}/approve", response_model=ClubSummary)
def approve_club(
    club_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_user),
):
    ensure_admin(user)
    club = db.get(Club, club_id)
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")
    club.approved = True
    db.flush()
    session_members = db.execute(
        select(ClubMember).where(
            ClubMember.club_id == club_id,
            ClubMember.role == "leader",
        )
    ).scalars().all()
    if session_members:
        for member in session_members:
            member.status = "approved"
    else:
        db.add(
            ClubMember(
                club_id=club_id,
                user_email=club.created_by_email,
                role="leader",
                status="approved",
            )
        )
    return club_summary(db, club)


@router.get("/api/admin/leaders/pending", response_model=list[UserOut])
def pending_leaders(
    db: Session = Depends(get_db),
    user: User = Depends(get_user),
):
    ensure_admin(user)
    leaders = (
        db.execute(
            select(User)
            .where(User.role == "leader", User.is_approved == False)  # noqa: E712
            .order_by(User.username.asc())
        )
        .scalars()
        .all()
    )
    return [UserOut.model_validate(leader, from_attributes=True) for leader in leaders]


@router.post("/api/admin/leaders/{user_id}/approve", response_model=UserOut)
def approve_leader(
    user_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_user),
):
    ensure_admin(user)
    leader = db.get(User, user_id)
    if not leader or leader.role != "leader":
        raise HTTPException(status_code=404, detail="Leader not found")
    leader.is_approved = True
    db.flush()
    db.refresh(leader)
    return UserOut.model_validate(leader, from_attributes=True)

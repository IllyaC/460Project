from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..deps import ensure_leader, ensure_leader_role, get_db, get_user
from ..models import Club, ClubAnnouncement, ClubMember, Event, User
from ..schemas import AnnouncementCreate, AnnouncementOut, ClubCreate, ClubDetail, ClubSummary, EventCreate, EventOut
from ..services import club_detail, club_summary, serialize_event

router = APIRouter()


@router.post("/api/clubs", response_model=ClubSummary)
def create_club(
    payload: ClubCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_user),
):
    ensure_leader_role(user)
    club = Club(
        name=payload.name,
        description=payload.description,
        approved=False,
        created_by_email=user.email,
    )
    db.add(club)
    db.flush()
    db.add(
        ClubMember(
            club_id=club.id,
            user_email=user.email,
            role="leader",
            status="pending",
        )
    )
    return club_summary(db, club, user.email)


@router.get("/api/clubs", response_model=list[ClubSummary])
def list_clubs(
    db: Session = Depends(get_db),
    user: User = Depends(get_user),
    search: str | None = None,
    category: str | None = None,
    approved: bool | None = None,
):
    search = search.strip() if isinstance(search, str) else None
    category = category.strip() if isinstance(category, str) else None

    stmt = select(Club)
    if search:
        like_pattern = f"%{search.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Club.name).like(like_pattern),
                func.lower(Club.description).like(like_pattern),
            )
        )
    if category:
        stmt = stmt.where(Club.category == category)
    if approved is not None:
        stmt = stmt.where(Club.approved == approved)

    clubs = db.execute(stmt.order_by(Club.name.asc())).scalars().all()
    return [club_summary(db, club, user.email) for club in clubs]


@router.get("/api/clubs/mine", response_model=list[ClubSummary])
def my_clubs(db: Session = Depends(get_db), user: User = Depends(get_user)):
    memberships = (
        db.execute(
            select(ClubMember).where(
                ClubMember.user_email == user.email,
                ClubMember.status == "approved",
            )
        )
        .scalars()
        .all()
    )
    if not memberships:
        return []

    club_ids = {m.club_id for m in memberships}
    clubs = (
        db.execute(select(Club).where(Club.id.in_(club_ids)).order_by(Club.name.asc()))
        .scalars()
        .all()
    )
    return [club_summary(db, club, user.email) for club in clubs]


@router.get("/api/clubs/{club_id}", response_model=ClubDetail)
def get_club(
    club_id: int, db: Session = Depends(get_db), user: User = Depends(get_user)
):
    club = db.get(Club, club_id)
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")
    return club_detail(db, club, user.email)


@router.post("/api/clubs/{club_id}/join")
def join_club(
    club_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_user),
):
    club = db.get(Club, club_id)
    if not club or not club.approved:
        raise HTTPException(status_code=404, detail="Club not available")
    existing = db.execute(
        select(ClubMember).where(
            ClubMember.club_id == club_id,
            ClubMember.user_email == user.email,
        )
    ).scalar_one_or_none()
    if existing:
        if existing.status == "approved":
            return {"status": "approved", "message": "Already a member"}
        existing.status = "pending"
        existing.role = existing.role or "member"
        return {"status": "pending", "message": "Membership request updated"}
    db.add(
        ClubMember(
            club_id=club_id,
            user_email=user.email,
            role="member",
            status="pending",
        )
    )
    return {"status": "pending", "message": "Request submitted"}


@router.post("/api/clubs/{club_id}/leave")
def leave_club(
    club_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_user),
):
    club = db.get(Club, club_id)
    if not club:
        raise HTTPException(status_code=404, detail="Club not available")

    membership = db.execute(
        select(ClubMember).where(
            ClubMember.club_id == club_id,
            ClubMember.user_email == user.email,
        )
    ).scalar_one_or_none()

    if not membership or membership.status == "removed":
        raise HTTPException(status_code=404, detail="Membership not found")

    membership.status = "removed"
    return {"status": "removed"}


@router.post("/api/clubs/{club_id}/members/{member_email}/approve")
def approve_member(
    club_id: int,
    member_email: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_user),
):
    ensure_leader(db, club_id, user)
    membership = db.execute(
        select(ClubMember).where(
            ClubMember.club_id == club_id,
            ClubMember.user_email == member_email,
        )
    ).scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=404, detail="Member not found")
    membership.status = "approved"
    return {"status": "approved"}


@router.post("/api/clubs/{club_id}/announcements", response_model=AnnouncementOut)
def create_announcement(
    club_id: int,
    payload: AnnouncementCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_user),
):
    ensure_leader(db, club_id, user)
    club = db.get(Club, club_id)
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")
    announcement = ClubAnnouncement(
        club_id=club_id,
        title=payload.title,
        body=payload.body,
    )
    db.add(announcement)
    db.flush()
    db.refresh(announcement)
    return AnnouncementOut(
        id=announcement.id,
        title=announcement.title,
        body=announcement.body,
        created_at=announcement.created_at,
    )


@router.post("/api/clubs/{club_id}/events", response_model=EventOut)
def create_club_event(
    club_id: int,
    payload: EventCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_user),
):
    ensure_leader(db, club_id, user)
    club = db.get(Club, club_id)
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")
    data = payload.model_dump()
    data["club_id"] = club_id
    event = Event(**data)
    db.add(event)
    db.flush()
    db.refresh(event)
    return serialize_event(event, registrations=0)

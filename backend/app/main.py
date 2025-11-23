from datetime import datetime, timedelta
import os
from typing import Literal, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from .db import Base, engine, get_session
from .models import (
    Club,
    ClubAnnouncement,
    ClubMember,
    Event,
    Flag,
    Registration,
)
from .schemas import (
    AnnouncementCreate,
    AnnouncementOut,
    ClubCreate,
    ClubDetail,
    ClubMemberOut,
    ClubSummary,
    EventCreate,
    EventOut,
    FlagCreate,
    FlagOut,
    RegistrationCreate,
    RegistrationOut,
)

# Load .env
load_dotenv()

app = FastAPI(title="Campus Clubs & Events (FastAPI + SQLite)")

# CORS for localhost frontend
CORS_ORIGIN = os.getenv("CORS_ORIGIN", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[CORS_ORIGIN],
    allow_methods=["*"],
    allow_headers=["*"]
)


class UserContext:
    def __init__(self, email: str, role: Literal["student", "leader", "admin"]):
        self.email = email
        self.role = role


def get_user(
    x_user_email: str = Header(default="student@example.edu"),
    x_user_role: str = Header(default="student")
) -> UserContext:
    role = x_user_role.lower()
    if role not in {"student", "leader", "admin"}:
        raise HTTPException(status_code=400, detail="X-User-Role must be student, leader, or admin")
    return UserContext(email=x_user_email, role=role)


def get_db():
    with get_session() as session:
        yield session


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(engine)
    with get_session() as session:
        seed_data(session)


def seed_data(session: Session) -> None:
    ai_club = session.execute(select(Club).where(Club.name == "AI Club")).scalar_one_or_none()
    if not ai_club:
        ai_club = Club(
            name="AI Club",
            description="Hands-on meetups about ML, robotics, and automation.",
            approved=True,
            created_by_email="leader@school.edu",
        )
        session.add(ai_club)
        session.flush()
        session.add(
            ClubMember(
                club_id=ai_club.id,
                user_email="leader@school.edu",
                role="leader",
                status="approved",
            )
        )
        session.add(
            ClubAnnouncement(
                club_id=ai_club.id,
                title="Kickoff week",
                body="First meeting this Friday in ENG 101. Bring friends!",
            )
        )
        session.add(
            Event(
                club_id=ai_club.id,
                title="AI Club Workshop",
                starts_at=datetime.utcnow() + timedelta(days=2),
                location="ENG 101",
                capacity=2,
                price_cents=0,
                category="tech",
            )
        )

    music = session.execute(select(Club).where(Club.name == "Music Makers")).scalar_one_or_none()
    if not music:
        session.add(
            Club(
                name="Music Makers",
                description="Student musicians jamming and performing on campus.",
                approved=False,
                created_by_email="musiclead@school.edu",
            )
        )

    # Ensure at least one general campus event exists
    if not session.execute(select(Event).where(Event.club_id.is_(None))).first():
        session.add(
            Event(
                club_id=None,
                title="Campus Welcome Fair",
                starts_at=datetime.utcnow() + timedelta(days=1),
                location="Campus Quad",
                capacity=200,
                price_cents=0,
                category="general",
            )
        )


def serialize_event(event: Event, registrations: int) -> EventOut:
    return EventOut(
        id=event.id,
        title=event.title,
        starts_at=event.starts_at,
        location=event.location,
        capacity=event.capacity,
        price_cents=event.price_cents,
        category=event.category,
        club_id=event.club_id,
        registration_count=registrations or 0,
    )


def base_event_query():
    reg_count = func.count(Registration.id).label("registration_count")
    stmt = select(Event, reg_count).outerjoin(Registration).group_by(Event.id)
    return stmt, reg_count


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


def serialize_flag(flag: Flag) -> FlagOut:
    return FlagOut(
        id=flag.id,
        item_type=flag.item_type,
        item_id=flag.item_id,
        reason=flag.reason,
        user_email=flag.user_email,
        created_at=flag.created_at,
        resolved=flag.resolved,
    )


@app.post("/api/events", response_model=EventOut)
def create_event(
    payload: EventCreate,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_user),
):
    # Allow club leaders to attach to their club or admins/general to create campus events
    if payload.club_id:
        ensure_leader(db, payload.club_id, user)
    event = Event(**payload.model_dump())
    db.add(event)
    db.flush()
    db.refresh(event)
    return serialize_event(event, registrations=0)


@app.get("/api/events", response_model=list[EventOut])
def list_events(
    start: datetime | None = None,
    end: datetime | None = None,
    category: str | None = None,
    location: str | None = None,
    free_only: bool | None = None,
    sort: Literal["date", "popularity"] = "date",
    db: Session = Depends(get_db),
):
    stmt, reg_count = base_event_query()
    effective_start = start or datetime.utcnow()
    stmt = stmt.where(Event.starts_at >= effective_start)
    if end:
        stmt = stmt.where(Event.starts_at <= end)
    if category:
        stmt = stmt.where(Event.category == category)
    if location:
        stmt = stmt.where(func.lower(Event.location).like(f"%{location.lower()}%"))
    if free_only:
        stmt = stmt.where(Event.price_cents == 0)

    if sort == "popularity":
        stmt = stmt.order_by(reg_count.desc(), Event.starts_at.asc())
    else:
        stmt = stmt.order_by(Event.starts_at.asc())

    rows = db.execute(stmt).all()
    return [serialize_event(event, regs) for event, regs in rows]


@app.get("/api/events/trending", response_model=list[EventOut])
def trending_events(limit: int = 5, db: Session = Depends(get_db)):
    stmt, reg_count = base_event_query()
    stmt = (
        stmt.where(Event.starts_at >= datetime.utcnow())
        .order_by(reg_count.desc(), Event.starts_at.asc())
        .limit(limit)
    )
    rows = db.execute(stmt).all()
    return [serialize_event(event, regs) for event, regs in rows]


@app.post("/api/registrations")
def register(
    payload: RegistrationCreate,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_user),
):
    event = db.get(Event, payload.event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    current = db.execute(
        select(func.count(Registration.id)).where(Registration.event_id == event.id)
    ).scalar() or 0
    if event.capacity > 0 and current >= event.capacity:
        raise HTTPException(status_code=409, detail="Event is full")

    existing = db.execute(
        select(Registration).where(
            Registration.event_id == event.id,
            Registration.user_email == user.email,
        )
    ).scalar_one_or_none()
    if existing:
        return {"status": "ok", "registration_id": existing.id, "message": "Already registered"}

    registration = Registration(event_id=event.id, user_email=user.email)
    db.add(registration)
    db.flush()

    print(
        f"[EMAIL] to={registration.user_email} subj=Registration confirmed body=You're in for '{event.title}'"
    )
    print(
        f"[PUSH]  to={registration.user_email} title=Registration confirmed body=See you at {event.location}"
    )

    return {"status": "ok", "registration_id": registration.id}


@app.delete("/api/registrations/{event_id}")
def unregister(
    event_id: int,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_user),
):
    registration = db.execute(
        select(Registration).where(
            Registration.event_id == event_id,
            Registration.user_email == user.email,
        )
    ).scalar_one_or_none()
    if not registration:
        raise HTTPException(status_code=404, detail="Registration not found")

    db.delete(registration)
    return {"status": "unregistered"}


@app.get("/api/registrations/mine", response_model=list[RegistrationOut])
def my_registrations(
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_user),
):
    registrations = (
        db.execute(
            select(Registration)
            .where(Registration.user_email == user.email)
            .order_by(Registration.created_at.desc())
        )
        .scalars()
        .all()
    )

    if not registrations:
        return []

    event_ids = [r.event_id for r in registrations]
    events = (
        db.execute(select(Event).where(Event.id.in_(event_ids)))
        .scalars()
        .all()
    )
    counts = dict(
        db.execute(
            select(Registration.event_id, func.count(Registration.id))
            .where(Registration.event_id.in_(event_ids))
            .group_by(Registration.event_id)
        ).all()
    )
    events_by_id = {event.id: event for event in events}

    def sort_key(registration: Registration):
        event = events_by_id.get(registration.event_id)
        return event.starts_at if event else datetime.max

    results = []
    for reg in sorted(registrations, key=sort_key):
        event = events_by_id.get(reg.event_id)
        if not event:
            continue
        registration_count = counts.get(event.id, 0)
        results.append(
            RegistrationOut(id=reg.id, event=serialize_event(event, registration_count))
        )

    return results


@app.post("/api/clubs", response_model=ClubSummary)
def create_club(
    payload: ClubCreate,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_user),
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


def club_summary(db: Session, club: Club, user_email: Optional[str] = None) -> ClubSummary:
    membership_status = None
    if user_email:
        membership = (
            db.execute(
                select(ClubMember).where(
                    ClubMember.club_id == club.id,
                    ClubMember.user_email == user_email,
                )
            )
            .scalars()
            .first()
        )
        if membership:
            membership_status = membership.status

    member_count = (
        db.execute(
            select(func.count(ClubMember.id)).where(
                ClubMember.club_id == club.id,
                ClubMember.status == "approved",
            )
        ).scalar()
        or 0
    )
    upcoming_events = (
        db.execute(
            select(func.count(Event.id)).where(
                Event.club_id == club.id,
                Event.starts_at >= datetime.utcnow(),
            )
        ).scalar()
        or 0
    )
    return ClubSummary(
        id=club.id,
        name=club.name,
        description=club.description,
        approved=club.approved,
        created_by_email=club.created_by_email,
        member_count=member_count,
        upcoming_event_count=upcoming_events,
        membership_status=membership_status,
    )


@app.get("/api/clubs", response_model=list[ClubSummary])
def list_clubs(db: Session = Depends(get_db), user: UserContext = Depends(get_user)):
    clubs = db.execute(select(Club).order_by(Club.name.asc())).scalars().all()
    return [club_summary(db, club, user.email) for club in clubs]


@app.get("/api/clubs/mine", response_model=list[ClubSummary])
def my_clubs(db: Session = Depends(get_db), user: UserContext = Depends(get_user)):
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


@app.get("/api/clubs/{club_id}", response_model=ClubDetail)
def get_club(
    club_id: int, db: Session = Depends(get_db), user: UserContext = Depends(get_user)
):
    club = db.get(Club, club_id)
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")
    summary = club_summary(db, club, user.email)
    members = (
        db.execute(select(ClubMember).where(ClubMember.club_id == club.id))
        .scalars()
        .all()
    )
    member_out = [
        ClubMemberOut(user_email=m.user_email, role=m.role, status=m.status)
        for m in members
    ]
    announcements = (
        db.execute(
            select(ClubAnnouncement)
            .where(ClubAnnouncement.club_id == club.id)
            .order_by(ClubAnnouncement.created_at.desc())
            .limit(5)
        )
        .scalars()
        .all()
    )
    announcement_out = [
        AnnouncementOut(
            id=a.id,
            title=a.title,
            body=a.body,
            created_at=a.created_at,
        )
        for a in announcements
    ]
    stmt, reg_count = base_event_query()
    stmt = (
        stmt.where(Event.club_id == club.id, Event.starts_at >= datetime.utcnow())
        .order_by(Event.starts_at.asc())
        .limit(5)
    )
    events = [serialize_event(event, regs) for event, regs in db.execute(stmt).all()]
    return ClubDetail(club=summary, members=member_out, announcements=announcement_out, events=events)


@app.post("/api/clubs/{club_id}/join")
def join_club(
    club_id: int,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_user),
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


@app.post("/api/clubs/{club_id}/leave")
def leave_club(
    club_id: int,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_user),
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


@app.post("/api/clubs/{club_id}/members/{member_email}/approve")
def approve_member(
    club_id: int,
    member_email: str,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_user),
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


@app.post("/api/clubs/{club_id}/announcements", response_model=AnnouncementOut)
def create_announcement(
    club_id: int,
    payload: AnnouncementCreate,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_user),
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


@app.post("/api/clubs/{club_id}/events", response_model=EventOut)
def create_club_event(
    club_id: int,
    payload: EventCreate,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_user),
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


@app.post("/api/flags", response_model=FlagOut)
def create_flag(
    payload: FlagCreate,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_user),
):
    item_type = payload.item_type.lower()
    if item_type not in {"event", "announcement"}:
        raise HTTPException(status_code=400, detail="item_type must be event or announcement")
    flag = Flag(
        item_type=item_type,
        item_id=payload.item_id,
        reason=payload.reason,
        user_email=user.email,
    )
    db.add(flag)
    db.flush()
    db.refresh(flag)
    return serialize_flag(flag)


@app.get("/api/admin/flags", response_model=list[FlagOut])
def list_flags(
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_user),
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


@app.post("/api/admin/flags/{flag_id}/resolve", response_model=FlagOut)
def resolve_flag(
    flag_id: int,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_user),
):
    ensure_admin(user)
    flag = db.get(Flag, flag_id)
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")
    flag.resolved = True
    db.flush()
    db.refresh(flag)
    return serialize_flag(flag)


@app.get("/api/admin/clubs/pending", response_model=list[ClubSummary])
def pending_clubs(
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_user),
):
    ensure_admin(user)
    clubs = (
        db.execute(select(Club).where(Club.approved == False).order_by(Club.name.asc()))  # noqa: E712
        .scalars()
        .all()
    )
    return [club_summary(db, club) for club in clubs]


@app.post("/api/admin/clubs/{club_id}/approve", response_model=ClubSummary)
def approve_club(
    club_id: int,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_user),
):
    ensure_admin(user)
    club = db.get(Club, club_id)
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")
    club.approved = True
    db.flush()
    # Ensure at least one leader membership is approved
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

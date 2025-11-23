from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Club, ClubAnnouncement, ClubMember, Event, Flag, Registration
from .schemas import (
    AnnouncementOut,
    ClubDetail,
    ClubMemberOut,
    ClubSummary,
    EventOut,
    FlagOut,
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


def club_summary(db: Session, club: Club, user_email: Optional[str] = None) -> ClubSummary:
    membership_status = None
    membership_role = None
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
            membership_role = membership.role

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
        membership_role=membership_role,
    )


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


def club_detail(db: Session, club: Club, user_email: str | None):
    summary = club_summary(db, club, user_email)
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

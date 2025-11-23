from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ..deps import ensure_admin, ensure_leader, get_db, get_user
from ..models import Event, Registration, User
from ..schemas import EventCreate, EventOut, RegistrationCreate, RegistrationOut
from ..services import base_event_query, serialize_event

router = APIRouter()


@router.post("/api/events", response_model=EventOut)
def create_event(
    payload: EventCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_user),
):
    if payload.club_id:
        ensure_leader(db, payload.club_id, user)
    event = Event(**payload.model_dump())
    db.add(event)
    db.flush()
    db.refresh(event)
    return serialize_event(event, registrations=0)


@router.get("/api/events", response_model=list[EventOut])
def list_events(
    start: datetime | None = None,
    end: datetime | None = None,
    category: str | None = None,
    title: str | None = None,
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
    if title:
        stmt = stmt.where(func.lower(Event.title).like(f"%{title.lower()}%"))
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


@router.get("/api/events/trending", response_model=list[EventOut])
def trending_events(limit: int = 5, db: Session = Depends(get_db)):
    stmt, reg_count = base_event_query()
    stmt = (
        stmt.where(Event.starts_at >= datetime.utcnow())
        .order_by(reg_count.desc(), Event.starts_at.asc())
        .limit(limit)
    )
    rows = db.execute(stmt).all()
    return [serialize_event(event, regs) for event, regs in rows]


@router.delete("/api/events/{event_id}")
def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_user),
):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.club_id:
        ensure_leader(db, event.club_id, user)
    else:
        ensure_admin(user)

    db.execute(delete(Registration).where(Registration.event_id == event.id))
    db.delete(event)
    return {"status": "deleted"}


@router.post("/api/registrations")
def register(
    payload: RegistrationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_user),
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


@router.delete("/api/registrations/{event_id}")
def unregister(
    event_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_user),
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


@router.get("/api/registrations/mine", response_model=list[RegistrationOut])
def my_registrations(
    db: Session = Depends(get_db),
    user: User = Depends(get_user),
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

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

from .db import Base, engine, get_session
from .models import Event, Registration
from .schemas import EventCreate, EventOut, RegistrationCreate

# Load .env
load_dotenv()

app = FastAPI(title="Campus Clubs & Events (FastAPI + SQLite)")

# CORS for localhost frontend
CORS_ORIGIN = os.getenv("CORS_ORIGIN", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[CORS_ORIGIN],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    Base.metadata.create_all(engine)
    # seed a couple of events if empty
    with get_session() as s:
        if not s.execute(select(Event).limit(1)).scalar_one_or_none():
            s.add_all([
                Event(title="Welcome Fair", starts_at=datetime.utcnow()+timedelta(days=1),
                      location="Quad", capacity=2, price_cents=0, category="general"),
                Event(title="AI Club Talk", starts_at=datetime.utcnow()+timedelta(days=3),
                      location="ENG 101", capacity=3, price_cents=0, category="tech"),
            ])

def get_db():
    with get_session() as s:
        yield s

@app.post("/api/events", response_model=EventOut)
def create_event(payload: EventCreate, db: Session = Depends(get_db)):
    ev = Event(**payload.model_dump())
    db.add(ev); db.flush(); db.refresh(ev)
    return EventOut(**{
        "id": ev.id, "title": ev.title, "starts_at": ev.starts_at,
        "location": ev.location, "capacity": ev.capacity,
        "price_cents": ev.price_cents, "category": ev.category
    })

@app.get("/api/events", response_model=list[EventOut])
def list_events(
    start: datetime | None = None,
    end: datetime | None = None,
    category: str | None = None,
    free_only: bool | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(Event)
    if start: stmt = stmt.where(Event.starts_at >= start)
    if end:   stmt = stmt.where(Event.starts_at <= end)
    if category: stmt = stmt.where(Event.category == category)
    if free_only: stmt = stmt.where(Event.price_cents == 0)
    stmt = stmt.order_by(Event.starts_at.asc())
    rows = db.execute(stmt).scalars().all()
    return [EventOut(**{
        "id": e.id, "title": e.title, "starts_at": e.starts_at,
        "location": e.location, "capacity": e.capacity,
        "price_cents": e.price_cents, "category": e.category
    }) for e in rows]

@app.post("/api/registrations")
def register(payload: RegistrationCreate, db: Session = Depends(get_db)):
    ev = db.get(Event, payload.event_id)
    if not ev:
        raise HTTPException(404, "Event not found")

    current = db.execute(select(func.count(Registration.id)).where(Registration.event_id == ev.id)).scalar() or 0
    if ev.capacity > 0 and current >= ev.capacity:
        raise HTTPException(409, "Event is full")

    # Demo user (no auth): fixed email; can be extended to read a header
    reg = Registration(event_id=ev.id, user_email="student@example.edu")
    db.add(reg); db.flush(); db.refresh(reg)

    # “Observer” demo: print two notifications to console
    print(f"[EMAIL] to={reg.user_email} subj=Registration confirmed body=You're in for '{ev.title}'")
    print(f"[PUSH]  to={reg.user_email} title=Registration confirmed body=See you at {ev.location}")

    return {"status": "ok", "registration_id": reg.id}

from datetime import datetime, timedelta
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from .api import admin, clubs, events, flags
from .db import Base, engine, get_session
from .deps import get_db, get_user
from .models import Club, ClubAnnouncement, ClubMember, Event

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


app.include_router(events.router)
app.include_router(clubs.router)
app.include_router(admin.router)
app.include_router(flags.router)

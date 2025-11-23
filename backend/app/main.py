from datetime import datetime, timedelta
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from .api import admin, auth, clubs, events, flags
from .auth_utils import hash_password
from .db import Base, engine, get_session
from .deps import get_db, get_user
from .models import Club, ClubAnnouncement, ClubMember, Event, Registration, User

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


def ensure_user(
    session: Session,
    username: str,
    email: str,
    role: str = "student",
    is_approved: bool = True,
    password: str = "password123",
) -> User:
    normalized_email = email.lower()
    existing = session.execute(select(User).where(User.email == normalized_email)).scalar_one_or_none()
    if existing:
        return existing
    base_username = username
    candidate_username = base_username
    suffix = 1
    while session.execute(select(User).where(User.username == candidate_username)).scalar_one_or_none():
        candidate_username = f"{base_username}{suffix}"
        suffix += 1
    user = User(
        username=candidate_username,
        email=normalized_email,
        password_hash=hash_password(password),
        role=role,
        is_approved=is_approved,
    )
    session.add(user)
    session.flush()
    return user


def seed_data(session: Session) -> None:
    ensure_user(
        session,
        username="admin",
        email="admin@school.edu",
        role="admin",
        is_approved=True,
        password="admin123",
    )

    leader_emails = {
        "leader@school.edu",
        "newleader@school.edu",
        "musiclead@school.edu",
        "traillead@school.edu",
        "careercoach@school.edu",
        "servicelead@school.edu",
        "artlead@school.edu",
        "foodlead@school.edu",
        "esportslead@school.edu",
        "wellnesslead@school.edu",
        "makerlead@school.edu",
    }
    for email in leader_emails:
        ensure_user(
            session,
            username=email.split("@")[0],
            email=email,
            role="leader",
            is_approved=True,
        )

    student_emails = {
        "student1@school.edu",
        "student@school.edu",
        "studenta@school.edu",
        "studentb@school.edu",
        "reggie@school.edu",
        "learner@school.edu",
        "one@school.edu",
        "two@school.edu",
        "self@school.edu",
        "joiner@school.edu",
        "member@school.edu",
        "flagger@school.edu",
        "studentA@school.edu",
        "studentB@school.edu",
        "student@example.edu",
    }
    for email in student_emails:
        ensure_user(
            session,
            username=email.split("@")[0],
            email=email,
            role="student",
            is_approved=True,
        )

    existing_clubs = session.execute(select(func.count(Club.id))).scalar_one()
    existing_events = session.execute(select(func.count(Event.id))).scalar_one()
    if existing_clubs > 0 or existing_events > 0:
        return

    now = datetime.utcnow()
    registration_counter = 1

    clubs_to_seed = [
        {
            "name": "AI Club",
            "description": "Hands-on meetups about ML, robotics, and automation.",
            "approved": True,
            "created_by_email": "leader@school.edu",
            "announcement": {
                "title": "Kickoff week",
                "body": "First meeting this Friday in ENG 101. Bring friends!",
            },
            "events": [
                {
                    "title": "Intro to Machine Learning",
                    "days_from_now": 2,
                    "location": "ENG 101",
                    "capacity": 60,
                    "price_cents": 0,
                    "category": "tech",
                    "registrations": 45,
                },
                {
                    "title": "Robotics Demo Night",
                    "days_from_now": 9,
                    "location": "Innovation Lab",
                    "capacity": 40,
                    "price_cents": 500,
                    "category": "tech",
                    "registrations": 22,
                },
                {
                    "title": "AI Ethics Roundtable",
                    "days_from_now": 16,
                    "location": "Library Auditorium",
                    "capacity": 80,
                    "price_cents": 0,
                    "category": "tech",
                    "registrations": 33,
                },
            ],
        },
        {
            "name": "Music Makers",
            "description": "Student musicians jamming and performing on campus.",
            "approved": True,
            "created_by_email": "musiclead@school.edu",
            "events": [
                {
                    "title": "Open Mic on the Quad",
                    "days_from_now": 3,
                    "location": "Campus Green",
                    "capacity": 120,
                    "price_cents": 0,
                    "category": "music",
                    "registrations": 65,
                },
                {
                    "title": "Songwriting Workshop",
                    "days_from_now": 11,
                    "location": "Arts Center 204",
                    "capacity": 35,
                    "price_cents": 1000,
                    "category": "music",
                    "registrations": 18,
                },
                {
                    "title": "Jazz Night at the Cafe",
                    "days_from_now": 20,
                    "location": "Student Cafe",
                    "capacity": 70,
                    "price_cents": 800,
                    "category": "music",
                    "registrations": 50,
                },
            ],
        },
        {
            "name": "Outdoor Adventures",
            "description": "Weekly hikes, day trips, and outdoor skills sessions.",
            "approved": True,
            "created_by_email": "traillead@school.edu",
            "events": [
                {
                    "title": "Sunrise Hike",
                    "days_from_now": 4,
                    "location": "Pine Ridge Trailhead",
                    "capacity": 25,
                    "price_cents": 0,
                    "category": "sports",
                    "registrations": 20,
                },
                {
                    "title": "Backpacking Basics",
                    "days_from_now": 13,
                    "location": "Rec Center Studio B",
                    "capacity": 30,
                    "price_cents": 0,
                    "category": "sports",
                    "registrations": 12,
                },
                {
                    "title": "Kayak on the River",
                    "days_from_now": 22,
                    "location": "River Dock",
                    "capacity": 18,
                    "price_cents": 1500,
                    "category": "sports",
                    "registrations": 10,
                },
            ],
        },
        {
            "name": "Career Launchpad",
            "description": "Networking, interview prep, and resume reviews to jumpstart your career.",
            "approved": True,
            "created_by_email": "careercoach@school.edu",
            "events": [
                {
                    "title": "Resume Review Sprint",
                    "days_from_now": 5,
                    "location": "Career Center",
                    "capacity": 50,
                    "price_cents": 0,
                    "category": "career",
                    "registrations": 38,
                },
                {
                    "title": "Tech Internship Panel",
                    "days_from_now": 12,
                    "location": "Hall A",
                    "capacity": 120,
                    "price_cents": 0,
                    "category": "career",
                    "registrations": 95,
                },
                {
                    "title": "LinkedIn Headshots",
                    "days_from_now": 19,
                    "location": "Media Lab",
                    "capacity": 40,
                    "price_cents": 1500,
                    "category": "career",
                    "registrations": 30,
                },
            ],
        },
        {
            "name": "Community Service Coalition",
            "description": "Volunteer projects focused on local impact and mutual aid.",
            "approved": True,
            "created_by_email": "servicelead@school.edu",
            "events": [
                {
                    "title": "Campus Cleanup Blitz",
                    "days_from_now": 6,
                    "location": "Main Quad",
                    "capacity": 80,
                    "price_cents": 0,
                    "category": "volunteer",
                    "registrations": 55,
                },
                {
                    "title": "Community Garden Workday",
                    "days_from_now": 14,
                    "location": "Campus Garden",
                    "capacity": 35,
                    "price_cents": 0,
                    "category": "community",
                    "registrations": 28,
                },
                {
                    "title": "Food Bank Packing",
                    "days_from_now": 24,
                    "location": "Service Hub",
                    "capacity": 60,
                    "price_cents": 0,
                    "category": "volunteer",
                    "registrations": 40,
                },
            ],
        },
        {
            "name": "Visual Arts Collective",
            "description": "Painting, photography, and gallery visits for art lovers.",
            "approved": True,
            "created_by_email": "artlead@school.edu",
            "events": [
                {
                    "title": "Campus Mural Walk",
                    "days_from_now": 7,
                    "location": "Arts District",
                    "capacity": 40,
                    "price_cents": 0,
                    "category": "arts",
                    "registrations": 25,
                },
                {
                    "title": "Ceramics Open Studio",
                    "days_from_now": 15,
                    "location": "Studio 12",
                    "capacity": 20,
                    "price_cents": 2000,
                    "category": "arts",
                    "registrations": 18,
                },
                {
                    "title": "Photography Night Shoot",
                    "days_from_now": 26,
                    "location": "Downtown Plaza",
                    "capacity": 25,
                    "price_cents": 0,
                    "category": "arts",
                    "registrations": 15,
                },
            ],
        },
        {
            "name": "Global Eats Club",
            "description": "Foodies exploring cuisines from around the world each week.",
            "approved": True,
            "created_by_email": "foodlead@school.edu",
            "events": [
                {
                    "title": "Dim Sum Brunch",
                    "days_from_now": 8,
                    "location": "Union Ballroom",
                    "capacity": 90,
                    "price_cents": 1800,
                    "category": "social",
                    "registrations": 70,
                },
                {
                    "title": "Mediterranean Cook-Along",
                    "days_from_now": 17,
                    "location": "Teaching Kitchen",
                    "capacity": 28,
                    "price_cents": 1200,
                    "category": "social",
                    "registrations": 24,
                },
                {
                    "title": "Spice Market Tour",
                    "days_from_now": 27,
                    "location": "City Market",
                    "capacity": 45,
                    "price_cents": 900,
                    "category": "social",
                    "registrations": 30,
                },
            ],
        },
        {
            "name": "Esports League",
            "description": "Competitive and casual gaming tournaments across popular titles.",
            "approved": True,
            "created_by_email": "esportslead@school.edu",
            "events": [
                {
                    "title": "Campus Overwatch Cup",
                    "days_from_now": 9,
                    "location": "Game Lab",
                    "capacity": 32,
                    "price_cents": 500,
                    "category": "gaming",
                    "registrations": 28,
                },
                {
                    "title": "Smash Bros Bracket",
                    "days_from_now": 18,
                    "location": "Student Center",
                    "capacity": 48,
                    "price_cents": 700,
                    "category": "gaming",
                    "registrations": 42,
                },
                {
                    "title": "Indie Games Showcase",
                    "days_from_now": 25,
                    "location": "Media Lounge",
                    "capacity": 50,
                    "price_cents": 0,
                    "category": "gaming",
                    "registrations": 33,
                },
            ],
        },
        {
            "name": "Wellness & Mindfulness",
            "description": "Meditation, yoga, and mental health peer support.",
            "approved": True,
            "created_by_email": "wellnesslead@school.edu",
            "events": [
                {
                    "title": "Sunset Yoga",
                    "days_from_now": 10,
                    "location": "Roof Garden",
                    "capacity": 50,
                    "price_cents": 0,
                    "category": "wellness",
                    "registrations": 40,
                },
                {
                    "title": "Guided Meditation",
                    "days_from_now": 21,
                    "location": "Reflection Room",
                    "capacity": 30,
                    "price_cents": 0,
                    "category": "wellness",
                    "registrations": 22,
                },
                {
                    "title": "Stress-Free Finals Planning",
                    "days_from_now": 28,
                    "location": "Library Classroom",
                    "capacity": 60,
                    "price_cents": 0,
                    "category": "wellness",
                    "registrations": 35,
                },
            ],
        },
        {
            "name": "Makerspace Guild",
            "description": "Hands-on builds, 3D printing, and hardware hacks in the campus makerspace.",
            "approved": True,
            "created_by_email": "makerlead@school.edu",
            "events": [
                {
                    "title": "3D Printing Crash Course",
                    "days_from_now": 11,
                    "location": "Makerspace",
                    "capacity": 25,
                    "price_cents": 500,
                    "category": "tech",
                    "registrations": 20,
                },
                {
                    "title": "Arduino Hack Night",
                    "days_from_now": 20,
                    "location": "Innovation Lab",
                    "capacity": 35,
                    "price_cents": 0,
                    "category": "tech",
                    "registrations": 26,
                },
                {
                    "title": "Wearables Show & Tell",
                    "days_from_now": 29,
                    "location": "Design Studio",
                    "capacity": 30,
                    "price_cents": 1200,
                    "category": "tech",
                    "registrations": 18,
                },
            ],
        },
    ]

    for club_data in clubs_to_seed:
        club = Club(
            name=club_data["name"],
            description=club_data["description"],
            approved=club_data.get("approved", False),
            created_by_email=club_data["created_by_email"],
        )
        session.add(club)
        session.flush()

        session.add(
            ClubMember(
                club_id=club.id,
                user_email=club_data["created_by_email"],
                role="leader",
                status="approved",
            )
        )

        if announcement := club_data.get("announcement"):
            session.add(
                ClubAnnouncement(
                    club_id=club.id,
                    title=announcement["title"],
                    body=announcement["body"],
                )
            )

        for event_data in club_data["events"]:
            event = Event(
                club_id=club.id,
                title=event_data["title"],
                starts_at=now + timedelta(days=event_data["days_from_now"]),
                location=event_data["location"],
                capacity=event_data["capacity"],
                price_cents=event_data["price_cents"],
                category=event_data["category"],
            )
            session.add(event)
            session.flush()

            for _ in range(event_data.get("registrations", 0)):
                session.add(
                    Registration(
                        event_id=event.id,
                        user_email=f"attendee{registration_counter}@school.edu",
                    )
                )
                registration_counter += 1

    campus_events = [
        {
            "title": "Campus Welcome Fair",
            "days_from_now": 1,
            "location": "Campus Quad",
            "capacity": 300,
            "price_cents": 0,
            "category": "general",
            "registrations": 220,
        },
        {
            "title": "Spring Concert",
            "days_from_now": 5,
            "location": "Main Lawn Stage",
            "capacity": 500,
            "price_cents": 2500,
            "category": "music",
            "registrations": 410,
        },
        {
            "title": "Startup Expo",
            "days_from_now": 12,
            "location": "Innovation Hall",
            "capacity": 200,
            "price_cents": 0,
            "category": "tech",
            "registrations": 160,
        },
        {
            "title": "Community Volunteer Day",
            "days_from_now": 18,
            "location": "Service Pavilion",
            "capacity": 250,
            "price_cents": 0,
            "category": "volunteer",
            "registrations": 180,
        },
        {
            "title": "International Food Fest",
            "days_from_now": 23,
            "location": "Global Village",
            "capacity": 350,
            "price_cents": 1500,
            "category": "social",
            "registrations": 290,
        },
    ]

    for campus_event in campus_events:
        event = Event(
            club_id=None,
            title=campus_event["title"],
            starts_at=now + timedelta(days=campus_event["days_from_now"]),
            location=campus_event["location"],
            capacity=campus_event["capacity"],
            price_cents=campus_event["price_cents"],
            category=campus_event["category"],
        )
        session.add(event)
        session.flush()

        for _ in range(campus_event.get("registrations", 0)):
            session.add(
                Registration(
                    event_id=event.id,
                    user_email=f"attendee{registration_counter}@school.edu",
                )
            )
            registration_counter += 1


app.include_router(auth.router)
app.include_router(events.router)
app.include_router(clubs.router)
app.include_router(admin.router)
app.include_router(flags.router)

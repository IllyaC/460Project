from datetime import datetime, timedelta

try:  # pragma: no cover - only executed when httpx is missing
    import httpx  # type: ignore # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - used in offline environments
    from .httpx_stub import install_httpx_stub

    install_httpx_stub()

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.main import app, get_db, seed_data
from app import models

TEST_DB_URL = "sqlite:///./test_clubs.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def override_get_db():
    session = TestingSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def auth_headers(email: str, role: str) -> dict[str, str]:
    return {"X-User-Email": email, "X-User-Role": role}


@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestingSessionLocal() as session:
        seed_data(session)
        session.commit()
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def test_list_events_basic(client):
    response = client.get("/api/events", headers=auth_headers("student1@school.edu", "student"))
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list) and data
    required_keys = {
        "id",
        "title",
        "starts_at",
        "location",
        "capacity",
        "price_cents",
        "category",
        "registration_count",
    }
    for event in data:
        assert required_keys.issubset(event.keys())


def test_event_filters_and_trending(client):
    admin_headers = auth_headers("admin@school.edu", "admin")
    start_time = datetime.utcnow() + timedelta(days=5)
    event_payloads = [
        {
            "title": "Soccer Match",
            "starts_at": (start_time).isoformat(),
            "location": "Field A",
            "capacity": 10,
            "price_cents": 0,
            "category": "sports",
            "club_id": None,
        },
        {
            "title": "Coding Jam",
            "starts_at": (start_time + timedelta(hours=1)).isoformat(),
            "location": "Lab 2",
            "capacity": 15,
            "price_cents": 0,
            "category": "tech",
            "club_id": None,
        },
    ]
    created_ids = []
    for payload in event_payloads:
        resp = client.post("/api/events", json=payload, headers=admin_headers)
        assert resp.status_code == 200
        created_ids.append(resp.json()["id"])

    filter_resp = client.get(
        "/api/events",
        params={"category": "sports"},
        headers=auth_headers("student@school.edu", "student"),
    )
    assert filter_resp.status_code == 200
    filtered = filter_resp.json()
    assert all(event["category"] == "sports" for event in filtered)

    # Create registrations to affect trending order
    student_a = auth_headers("studentA@school.edu", "student")
    student_b = auth_headers("studentB@school.edu", "student")
    client.post("/api/registrations", json={"event_id": created_ids[0]}, headers=student_a)
    client.post("/api/registrations", json={"event_id": created_ids[0]}, headers=student_b)
    client.post("/api/registrations", json={"event_id": created_ids[1]}, headers=student_a)

    trending_resp = client.get("/api/events/trending", headers=student_a)
    assert trending_resp.status_code == 200
    trending = trending_resp.json()
    assert trending[0]["registration_count"] >= trending[1]["registration_count"]
    if trending[0]["registration_count"] == trending[1]["registration_count"]:
        assert trending[0]["starts_at"] <= trending[1]["starts_at"]


def test_successful_registration_and_duplicate_registration(client):
    admin_headers = auth_headers("admin@school.edu", "admin")
    event_resp = client.post(
        "/api/events",
        json={
            "title": "Large Workshop",
            "starts_at": (datetime.utcnow() + timedelta(days=3)).isoformat(),
            "location": "Hall 1",
            "capacity": 3,
            "price_cents": 0,
            "category": "tech",
            "club_id": None,
        },
        headers=admin_headers,
    )
    event_id = event_resp.json()["id"]

    headers_student = auth_headers("learner@school.edu", "student")
    first = client.post(
        "/api/registrations",
        json={"event_id": event_id},
        headers=headers_student,
    )
    assert first.status_code == 200
    reg_id = first.json()["registration_id"]

    second = client.post(
        "/api/registrations",
        json={"event_id": event_id},
        headers=headers_student,
    )
    assert second.status_code == 200
    assert second.json()["registration_id"] == reg_id

    with TestingSessionLocal() as session:
        regs = session.execute(
            select(models.Registration).where(models.Registration.event_id == event_id)
        ).scalars().all()
        assert len(regs) == 1


def test_registration_capacity_limit(client):
    admin_headers = auth_headers("admin@school.edu", "admin")
    event_resp = client.post(
        "/api/events",
        json={
            "title": "Limited Talk",
            "starts_at": (datetime.utcnow() + timedelta(days=2)).isoformat(),
            "location": "Room B",
            "capacity": 1,
            "price_cents": 0,
            "category": "general",
            "club_id": None,
        },
        headers=admin_headers,
    )
    event_id = event_resp.json()["id"]

    first = client.post(
        "/api/registrations",
        json={"event_id": event_id},
        headers=auth_headers("one@school.edu", "student"),
    )
    assert first.status_code == 200

    second = client.post(
        "/api/registrations",
        json={"event_id": event_id},
        headers=auth_headers("two@school.edu", "student"),
    )
    assert second.status_code == 409


def test_club_creation_and_admin_approval(client):
    leader_headers = auth_headers("newleader@school.edu", "leader")
    create_resp = client.post(
        "/api/clubs",
        json={"name": "Chess Stars", "description": "Chess strategy sessions"},
        headers=leader_headers,
    )
    assert create_resp.status_code == 200
    club = create_resp.json()
    assert club["approved"] is False
    club_id = club["id"]

    pending_resp = client.get(
        "/api/admin/clubs/pending",
        headers=auth_headers("admin@school.edu", "admin"),
    )
    assert pending_resp.status_code == 200
    pending_ids = [c["id"] for c in pending_resp.json()]
    assert club_id in pending_ids

    approve_resp = client.post(
        f"/api/admin/clubs/{club_id}/approve",
        headers=auth_headers("admin@school.edu", "admin"),
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["approved"] is True

    with TestingSessionLocal() as session:
        leaders = session.execute(
            select(models.ClubMember).where(
                models.ClubMember.club_id == club_id,
                models.ClubMember.role == "leader",
                models.ClubMember.status == "approved",
            )
        ).scalars().all()
        assert leaders


def test_join_club_and_approval_flow(client):
    with TestingSessionLocal() as session:
        club = session.execute(
            select(models.Club).where(models.Club.approved == True)
        ).scalar_one()
        club_id = club.id

    student_headers = auth_headers("joiner@school.edu", "student")
    join_resp = client.post(f"/api/clubs/{club_id}/join", headers=student_headers)
    assert join_resp.status_code == 200

    with TestingSessionLocal() as session:
        membership = session.execute(
            select(models.ClubMember).where(
                models.ClubMember.club_id == club_id,
                models.ClubMember.user_email == "joiner@school.edu",
            )
        ).scalar_one()
        assert membership.status == "pending"

    leader_headers = auth_headers("leader@school.edu", "leader")
    approve_resp = client.post(
        f"/api/clubs/{club_id}/members/joiner@school.edu/approve",
        headers=leader_headers,
    )
    assert approve_resp.status_code == 200

    with TestingSessionLocal() as session:
        membership = session.execute(
            select(models.ClubMember).where(
                models.ClubMember.club_id == club_id,
                models.ClubMember.user_email == "joiner@school.edu",
            )
        ).scalar_one()
        assert membership.status == "approved"


def test_flag_creation_listing_and_resolution(client):
    with TestingSessionLocal() as session:
        event = session.execute(select(models.Event)).scalars().first()
        assert event is not None
        event_id = event.id

    student_headers = auth_headers("flagger@school.edu", "student")
    create_resp = client.post(
        "/api/flags",
        json={"item_type": "event", "item_id": event_id, "reason": "Inappropriate content"},
        headers=student_headers,
    )
    assert create_resp.status_code == 200
    created_flag = create_resp.json()
    assert created_flag["user_email"] == "flagger@school.edu"
    assert created_flag["resolved"] is False

    admin_headers = auth_headers("admin@school.edu", "admin")
    list_resp = client.get("/api/admin/flags", headers=admin_headers)
    assert list_resp.status_code == 200
    flags = list_resp.json()
    assert any(f["id"] == created_flag["id"] for f in flags)

    resolve_resp = client.post(
        f"/api/admin/flags/{created_flag['id']}/resolve",
        headers=admin_headers,
    )
    assert resolve_resp.status_code == 200
    resolved_flag = resolve_resp.json()
    assert resolved_flag["resolved"] is True

    list_after = client.get("/api/admin/flags", headers=admin_headers)
    assert list_after.status_code == 200
    assert all(f["id"] != created_flag["id"] for f in list_after.json())

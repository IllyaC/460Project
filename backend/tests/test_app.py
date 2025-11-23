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


def get_club_id_by_name(name: str) -> int:
    with TestingSessionLocal() as session:
        club = (
            session.execute(select(models.Club).where(models.Club.name == name))
            .scalars()
            .first()
        )
        assert club is not None
        return club.id


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


def test_event_filter_by_title(client):
    admin_headers = auth_headers("admin@school.edu", "admin")
    start_time = datetime.utcnow() + timedelta(days=6)
    jam_event = {
        "title": "Coding Jam Session",
        "starts_at": (start_time).isoformat(),
        "location": "Lab 3",
        "capacity": 20,
        "price_cents": 0,
        "category": "tech",
        "club_id": None,
    }
    other_event = {
        "title": "Career Expo",
        "starts_at": (start_time + timedelta(hours=2)).isoformat(),
        "location": "Hall A",
        "capacity": 50,
        "price_cents": 0,
        "category": "career",
        "club_id": None,
    }

    for payload in (jam_event, other_event):
        create_resp = client.post("/api/events", json=payload, headers=admin_headers)
        assert create_resp.status_code == 200

    filter_resp = client.get(
        "/api/events",
        params={"title": "jam"},
        headers=auth_headers("student@school.edu", "student"),
    )
    assert filter_resp.status_code == 200
    results = filter_resp.json()
    assert results
    assert all("jam" in event["title"].lower() for event in results)


def test_leader_can_delete_owned_club_event(client):
    club_id = get_club_id_by_name("AI Club")
    leader_headers = auth_headers("leader@school.edu", "leader")
    payload = {
        "title": "Leader Only Event",
        "starts_at": (datetime.utcnow() + timedelta(days=3)).isoformat(),
        "location": "ENG 202",
        "capacity": 5,
        "price_cents": 0,
        "category": "tech",
    }

    create_resp = client.post(
        f"/api/clubs/{club_id}/events", json=payload, headers=leader_headers
    )
    assert create_resp.status_code == 200
    event_id = create_resp.json()["id"]

    delete_resp = client.delete(
        f"/api/events/{event_id}", headers=leader_headers
    )
    assert delete_resp.status_code == 200
    with TestingSessionLocal() as session:
        deleted = session.get(models.Event, event_id)
        assert deleted is None


def test_non_leader_cannot_delete_club_event(client):
    club_id = get_club_id_by_name("AI Club")
    leader_headers = auth_headers("leader@school.edu", "leader")
    payload = {
        "title": "Protected Event",
        "starts_at": (datetime.utcnow() + timedelta(days=2)).isoformat(),
        "location": "ENG 203",
        "capacity": 10,
        "price_cents": 0,
        "category": "tech",
    }
    create_resp = client.post(
        f"/api/clubs/{club_id}/events", json=payload, headers=leader_headers
    )
    event_id = create_resp.json()["id"]

    student_headers = auth_headers("student@school.edu", "student")
    delete_resp = client.delete(
        f"/api/events/{event_id}", headers=student_headers
    )
    assert delete_resp.status_code == 403
    with TestingSessionLocal() as session:
        still_exists = session.get(models.Event, event_id)
        assert still_exists is not None


def test_admin_can_delete_general_event(client):
    admin_headers = auth_headers("admin@school.edu", "admin")
    payload = {
        "title": "Admin Event",
        "starts_at": (datetime.utcnow() + timedelta(days=4)).isoformat(),
        "location": "Campus Center",
        "capacity": 25,
        "price_cents": 0,
        "category": "general",
        "club_id": None,
    }
    create_resp = client.post("/api/events", json=payload, headers=admin_headers)
    assert create_resp.status_code == 200
    event_id = create_resp.json()["id"]

    delete_resp = client.delete(
        f"/api/events/{event_id}", headers=admin_headers
    )
    assert delete_resp.status_code == 200


def test_deleting_event_removes_registrations(client):
    admin_headers = auth_headers("admin@school.edu", "admin")
    event_resp = client.post(
        "/api/events",
        json={
            "title": "Delete Me",
            "starts_at": (datetime.utcnow() + timedelta(days=2)).isoformat(),
            "location": "Hall C",
            "capacity": 10,
            "price_cents": 0,
            "category": "general",
            "club_id": None,
        },
        headers=admin_headers,
    )
    event_id = event_resp.json()["id"]

    student_headers = auth_headers("reggie@school.edu", "student")
    reg_resp = client.post(
        "/api/registrations",
        json={"event_id": event_id},
        headers=student_headers,
    )
    assert reg_resp.status_code == 200

    delete_resp = client.delete(f"/api/events/{event_id}", headers=admin_headers)
    assert delete_resp.status_code == 200

    with TestingSessionLocal() as session:
        assert session.get(models.Event, event_id) is None
        remaining_regs = session.execute(
            select(models.Registration).where(models.Registration.event_id == event_id)
        ).scalars().all()
        assert remaining_regs == []


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


def test_list_and_remove_my_registrations(client):
    admin_headers = auth_headers("admin@school.edu", "admin")
    student_headers = auth_headers("self@school.edu", "student")

    event_payloads = [
        {
            "title": "Workshop One",
            "starts_at": (datetime.utcnow() + timedelta(days=4)).isoformat(),
            "location": "Hall 2",
            "capacity": 5,
            "price_cents": 0,
            "category": "tech",
            "club_id": None,
        },
        {
            "title": "Workshop Two",
            "starts_at": (datetime.utcnow() + timedelta(days=5)).isoformat(),
            "location": "Hall 3",
            "capacity": 5,
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

    for event_id in created_ids:
        reg_resp = client.post(
            "/api/registrations",
            json={"event_id": event_id},
            headers=student_headers,
        )
        assert reg_resp.status_code == 200

    mine_resp = client.get("/api/registrations/mine", headers=student_headers)
    assert mine_resp.status_code == 200
    mine = mine_resp.json()
    returned_event_ids = {item["event"]["id"] for item in mine}
    assert set(created_ids).issubset(returned_event_ids)

    delete_resp = client.delete(
        f"/api/registrations/{created_ids[0]}", headers=student_headers
    )
    assert delete_resp.status_code == 200

    mine_after = client.get("/api/registrations/mine", headers=student_headers)
    assert mine_after.status_code == 200
    after_ids = {item["event"]["id"] for item in mine_after.json()}
    assert created_ids[0] not in after_ids
    assert created_ids[1] in after_ids


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


def test_my_clubs_and_leave_flow(client):
    with TestingSessionLocal() as session:
        club = session.execute(
            select(models.Club).where(models.Club.approved == True)
        ).scalar_one()
        club_id = club.id

    student_headers = auth_headers("member@school.edu", "student")
    join_resp = client.post(f"/api/clubs/{club_id}/join", headers=student_headers)
    assert join_resp.status_code == 200

    leader_headers = auth_headers("leader@school.edu", "leader")
    approve_resp = client.post(
        f"/api/clubs/{club_id}/members/member@school.edu/approve",
        headers=leader_headers,
    )
    assert approve_resp.status_code == 200

    mine_resp = client.get("/api/clubs/mine", headers=student_headers)
    assert mine_resp.status_code == 200
    mine_ids = {club["id"] for club in mine_resp.json()}
    assert club_id in mine_ids

    list_resp = client.get("/api/clubs", headers=student_headers)
    club_summary = next(c for c in list_resp.json() if c["id"] == club_id)
    assert club_summary["membership_status"] == "approved"

    leave_resp = client.post(f"/api/clubs/{club_id}/leave", headers=student_headers)
    assert leave_resp.status_code == 200

    mine_after = client.get("/api/clubs/mine", headers=student_headers).json()
    assert club_id not in {club["id"] for club in mine_after}

    list_after = client.get("/api/clubs", headers=student_headers).json()
    after_status = next(c for c in list_after if c["id"] == club_id)["membership_status"]
    assert after_status == "removed"


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


def test_flags_list_requires_admin_role(client):
    with TestingSessionLocal() as session:
        event = session.execute(select(models.Event)).scalars().first()
        assert event is not None
    create_resp = client.post(
        "/api/flags",
        json={"item_type": "event", "item_id": event.id, "reason": "spam"},
        headers=auth_headers("student@school.edu", "student"),
    )
    assert create_resp.status_code == 200

    list_resp = client.get("/api/admin/flags", headers=auth_headers("student@school.edu", "student"))
    assert list_resp.status_code == 403

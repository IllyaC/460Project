# Campus Clubs & Events (FastAPI + Express)

A lightweight campus activities portal that pairs a FastAPI backend (SQLite + SQLAlchemy) with a Node/Express static frontend. Phase 2 brings the experience to roughly 70% of the rubric with clubs, membership approvals, leader/admin roles, and richer discovery.

## Quick start
```bash
# from repo root
cp .env.example .env  # optional; DATABASE_URL defaults to sqlite:///./clubs.db

# backend (FastAPI + SQLite)
cd backend
python -m venv .venv && . .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# frontend (Express static app)
cd ../frontend
npm install
npm start  # serves http://localhost:3000
```

### Persona headers
Every API call reads `X-User-Email` (default `student@example.edu`) and `X-User-Role` (`student`, `leader`, or `admin`). The frontend’s "Persona" section lets you set these headers interactively:

| Persona | Email | Role | Use cases |
|---------|-------|------|-----------|
| Student | `student@example.edu` | `student` | Browse events, request to join clubs, register for events |
| AI Club Leader | `leader@school.edu` | `leader` | Approve members, post announcements, schedule leader-only events |
| Admin | `admin@school.edu` | `admin` | Approve pending clubs via the admin dashboard |

### Demo login credentials
The Express frontend now hides the dashboard behind a simple credential check that reads from `frontend/public/demo-credentials.txt`. The file ships with 5 students plus one leader and one admin so that every persona can be tested quickly:

| Email | Role | Password | Notes |
|-------|------|----------|-------|
| `amy.student@demo.edu` | student | `otter123` | General-purpose student #1 |
| `ben.student@demo.edu` | student | `summit234` | General-purpose student #2 |
| `cory.student@demo.edu` | student | `harbor345` | General-purpose student #3 |
| `dana.student@demo.edu` | student | `lumen456` | General-purpose student #4 |
| `eli.student@demo.edu` | student | `orbit567` | General-purpose student #5 |
| `leader@school.edu` | leader | `clubguide` | Pre-seeded AI Club leader |
| `admin@school.edu` | admin | `supervisor` | Campus admin reviewer |

To update or add credentials for future demos, edit the text file (format: `email,role,password`) and refresh the browser — the login form and quick-fill buttons repopulate automatically.

## API highlights
Key tables: `clubs`, `club_members`, `club_announcements`, `events`, and `registrations`. On startup the backend auto-creates tables and seeds:
- Approved **AI Club** with a leader (`leader@school.edu`), an announcement, and a capacity-2 workshop.
- A pending **Music Makers** club ready for admin approval.
- A general campus "Welcome Fair" event.

### Event discovery
- `GET /api/events` — supports `start`, `end`, `category`, `location`, `free_only`, and `sort=date|popularity` (popularity uses registration counts).
- `GET /api/events/trending?limit=5` — highest registration counts, handy for the Discover + Trending UI cards.
- `POST /api/events` — create campus-wide or club-scoped events (leaders can attach `club_id`).
- `POST /api/registrations` — enforces capacity, dedupes users, and prints faux email/push notifications.

### Clubs + membership
- `POST /api/clubs` — students submit clubs (auto-marked unapproved).
- `GET /api/clubs` — approved clubs with `memberCount` + `upcomingEventCount`.
- `GET /api/clubs/{id}` — aggregates the club summary, approved members, last 5 announcements, and next 5 events.
- `POST /api/clubs/{id}/join` — students request membership (status `pending`).
- `POST /api/clubs/{id}/members/{email}/approve` — leader-only approval flow.
- `POST /api/clubs/{id}/announcements` — leader-only broadcast board.
- `POST /api/clubs/{id}/events` — leader-only event creation scoped to that club.

### Admin review
- `GET /api/admin/clubs/pending` — requires `X-User-Role: admin`.
- `POST /api/admin/clubs/{id}/approve` — marks the club approved and unlocks its leaders.

### Curl snippets
```bash
# Discover free AI events
curl -s "http://localhost:8000/api/events?category=tech&free_only=true" | jq

# Student joins the AI Club
curl -s -X POST http://localhost:8000/api/clubs/1/join \
  -H 'X-User-Email: student@example.edu' -H 'X-User-Role: student' | jq

# Leader approves that member
curl -s -X POST http://localhost:8000/api/clubs/1/members/student@example.edu/approve \
  -H 'X-User-Email: leader@school.edu' -H 'X-User-Role: leader'

# Admin approves Music Makers
curl -s -X POST http://localhost:8000/api/admin/clubs/2/approve \
  -H 'X-User-Email: admin@school.edu' -H 'X-User-Role: admin'
```

## Frontend walkthrough
The single-page frontend (served by Express) now includes:
1. **Persona**: Set headers for email/role with quick-fill buttons.
2. **Discover**: Full-text filters, free-only toggle, sort selector, trending list, and registration buttons.
3. **Clubs**: Approved directory, create-club form, and join flow with realtime feedback.
4. **Club Page**: Load any club ID to see members, announcements, and events. Leaders can approve members, post announcements, and schedule club events.
5. **Admin**: Pending club queue plus inline approval.

## Rubric checklist (~70%)
- [x] Multi-stack app (FastAPI backend + Express frontend + SQLite persistence).
- [x] SQLAlchemy models for clubs, members, announcements, events (with club_id), and registrations.
- [x] Startup seeding: approved AI Club w/ leader, announcement, event, plus pending Music Makers.
- [x] Event discovery improvements (filters, trending, popularity sort, free-only toggle, registration limits/notifications).
- [x] Clubs API with creation, listings, aggregates, membership join/approve, announcements, and leader events.
- [x] Header-based personas with role checks (student / leader / admin) powering UI sections.
- [x] Admin review workflow for pending clubs.
- [x] Frontend demonstrates end-to-end flows (create→filter→register, join→approve, announce, leader events, admin approval).

## Verifying flows
Use this manual test to cover the login, student, leader, and admin experiences end-to-end:

1. **Launch the stack** (backend + frontend) and open http://localhost:3000.
2. **Log in as a student** using `amy.student@demo.edu` / `otter123`. Confirm the dashboard becomes visible and the header shows the Student persona.
3. **Event discovery & registration**
   - Run a search in "Discover events" and confirm the table populates.
   - Use "Create event" to add a new Hack Night; then register for it twice. A third registration attempt should return a 409 once the capacity is hit.
4. **Club interactions**
   - From the "Clubs directory", request to join the AI Club (ID 1).
   - Create a brand-new club submission so it appears in the pending queue later.
5. **Log out** (button in the persona card) and **log in as the leader** using `leader@school.edu` / `clubguide`.
   - Load Club 1, approve `amy.student@demo.edu`, post an announcement, and schedule a new club-specific event.
6. **Log out** and **log in as the admin** using `admin@school.edu` / `supervisor`.
   - Load the pending club list and approve the club that the student just submitted.
7. **Return to any student account** (e.g., `ben.student@demo.edu`) and refresh Discover + Trending to confirm that registration counts, club memberships, and admin-approved clubs are all reflected.

This sequence exercises the login gate, student-facing flows (discover, register, join), leader tools (approve, announce, schedule), and admin approvals without touching any credentials outside the demo text file.

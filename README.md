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
1. Start backend + frontend (see Quick start), then open http://localhost:3000.
2. As a **student**, create an event, filter events, and register twice (third attempt hits the 409 capacity guard).
3. As a **student**, request to join the AI Club, then switch to the **leader** persona to approve that email, post an announcement, and add a club event.
4. Switch to **admin** and approve "Music Makers" from the Admin dashboard (its leader membership unlocks automatically).
5. Check the Discover + Trending section to see registration counts update in realtime.

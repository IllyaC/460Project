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



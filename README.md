# Campus Clubs & Events (FastAPI + Express)

Campus Clubs & Events is a lightweight portal where students can browse or create events, join clubs, manage memberships, and flag content for administrators. The FastAPI backend uses SQLite + SQLAlchemy, and the Express frontend serves a demo-friendly single-page UI that talks to the API with persona headers.

## How to run the backend (FastAPI)
1. From the repo root, copy the sample environment file (optional):
   ```bash
   cp .env.example .env  # DATABASE_URL defaults to sqlite:///./clubs.db
   ```
2. Create and activate a virtual environment:
   ```bash
   cd backend
   python -m venv .venv && . .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the API server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

## How to run the frontend (Express static app)
1. Open a new shell so the backend can keep running, then from the repo root:
   ```bash
   cd frontend
   npm install
   ```
2. Start the static dev server:
   ```bash
   npm start
   ```
3. Visit http://localhost:3000 and use the persona controls to send the correct `X-User-Email` and `X-User-Role` headers to the API.



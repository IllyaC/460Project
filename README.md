

## Quick start
```bash
# from repo root
cp .env.example .env

# backend
cd backend
python -m venv .venv && . .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# frontend (new terminal)
cd ../frontend
npm install
npm start  # http://localhost:3000
```

Open http://localhost:3000 and click:
- Create an event (capacity 2)
- List with category / free-only
- Register twice (then 3rd -> 409 "Event is full")



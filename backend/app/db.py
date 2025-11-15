import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Load .env at repo root
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", ".env"))

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./clubs.db")

class Base(DeclarativeBase):
    pass

def _engine():
    # For SQLite in FastAPI, allow cross-thread access
    if DATABASE_URL.startswith("sqlite"):
        return create_engine(DATABASE_URL, echo=False, pool_pre_ping=True, connect_args={"check_same_thread": False})
    return create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

engine = _engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def get_session():
    from contextlib import contextmanager
    @contextmanager
    def _session_scope():
        session = SessionLocal()
        try:
            yield session
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()
    return _session_scope()

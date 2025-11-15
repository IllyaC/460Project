from pydantic import BaseModel
from datetime import datetime

class EventCreate(BaseModel):
    title: str
    starts_at: datetime
    location: str
    capacity: int = 0
    price_cents: int = 0
    category: str = "general"

class EventOut(BaseModel):
    id: int
    title: str
    starts_at: datetime
    location: str
    capacity: int
    price_cents: int
    category: str

class RegistrationCreate(BaseModel):
    event_id: int

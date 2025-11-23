from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


class EventCreate(BaseModel):
    title: str
    starts_at: datetime
    location: str
    capacity: int = 0
    price_cents: int = 0
    category: str = "general"
    club_id: Optional[int] = None


class EventOut(BaseModel):
    id: int
    title: str
    starts_at: datetime
    location: str
    capacity: int
    price_cents: int
    category: str
    club_id: Optional[int] = None
    registration_count: int = 0


class RegistrationCreate(BaseModel):
    event_id: int


class RegistrationOut(BaseModel):
    id: int
    event: EventOut


class ClubCreate(BaseModel):
    name: str
    description: str

    @field_validator("name", "description")
    @classmethod
    def must_not_be_empty(cls, value: str):
        cleaned = value.strip() if isinstance(value, str) else ""
        if not cleaned:
            raise ValueError("must not be empty")
        return cleaned


class ClubSummary(BaseModel):
    id: int
    name: str
    description: str
    approved: bool
    created_by_email: str
    member_count: int
    upcoming_event_count: int
    membership_status: Optional[str] = None
    membership_role: Optional[str] = None


class ClubMemberOut(BaseModel):
    user_email: str
    role: str
    status: str


class AnnouncementCreate(BaseModel):
    title: str
    body: str


class AnnouncementOut(BaseModel):
    id: int
    title: str
    body: str
    created_at: datetime


class ClubDetail(BaseModel):
    club: ClubSummary
    members: list[ClubMemberOut]
    announcements: list[AnnouncementOut]
    events: list[EventOut]


class FlagCreate(BaseModel):
    item_type: str
    item_id: int
    reason: str


class FlagOut(BaseModel):
    id: int
    item_type: str
    item_id: int
    reason: str
    user_email: str
    created_at: datetime
    resolved: bool

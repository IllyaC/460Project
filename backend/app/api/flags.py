from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_db, get_user, UserContext
from ..models import Flag
from ..schemas import FlagCreate, FlagOut
from ..services import serialize_flag

router = APIRouter()


@router.post("/api/flags", response_model=FlagOut)
def create_flag(
    payload: FlagCreate,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_user),
):
    item_type = payload.item_type.lower()
    if item_type not in {"event", "announcement"}:
        raise HTTPException(status_code=400, detail="item_type must be event or announcement")
    flag = Flag(
        item_type=item_type,
        item_id=payload.item_id,
        reason=payload.reason,
        user_email=user.email,
    )
    db.add(flag)
    db.flush()
    db.refresh(flag)
    return serialize_flag(flag)

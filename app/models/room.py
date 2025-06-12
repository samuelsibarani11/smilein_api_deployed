# app/models/room.py
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.schedule import Schedule

class Room(SQLModel, table=True):
    room_id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field()
    latitude: float = Field()
    longitude: float = Field()
    radius: float = Field(description="Radius in meters")
    
    # Relationship to schedules
    schedules: List["Schedule"] = Relationship(back_populates="room")
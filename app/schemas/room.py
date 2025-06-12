# app/schemas/room.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

class RoomBase(BaseModel):
    name: str
    latitude: float
    longitude: float
    radius: float = Field(description="Radius in meters")

class RoomCreate(RoomBase):
    pass

class RoomUpdate(BaseModel):
    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius: Optional[float] = None

class RoomResponse(RoomBase):
    room_id: int
    
    model_config = ConfigDict(from_attributes=True)
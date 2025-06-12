# app/schemas/schedule.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime, date

from app.schemas.course import CourseResponse
from app.schemas.instructor import InstructorResponse
from app.schemas.room import RoomResponse


class ScheduleBase(BaseModel):
    course_id: int
    instructor_id: Optional[int] = None
    room_id: Optional[int] = None
    chapter: Optional[str] = None
    schedule_date: date
    start_time: str
    end_time: str


class ScheduleCreate(ScheduleBase):
    pass


class ScheduleUpdate(BaseModel):
    course_id: Optional[int] = None
    instructor_id: Optional[int] = None
    room_id: Optional[int] = None
    chapter: Optional[str] = None
    schedule_date: Optional[date] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None

# app/schemas/schedule.py
class ScheduleRead(BaseModel):
    schedule_id: int
    room: Optional[RoomResponse]
    chapter: Optional[str]
    # day_of_week field removed
    schedule_date: date
    start_time: str
    end_time: str
    created_at: datetime
    course: Optional[CourseResponse]
    instructor: Optional[InstructorResponse]

    model_config = ConfigDict(from_attributes=True)
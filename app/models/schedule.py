# app/models/schedule.py
from sqlmodel import SQLModel, Field, Relationship
from typing import TYPE_CHECKING, Optional, List
from datetime import datetime, date

if TYPE_CHECKING:
    from app.models.instructor import Instructor
    from app.models.course import Course
    from app.models.attendance import Attendance
    from app.models.room import Room

# app/models/schedule.py
class Schedule(SQLModel, table=True):
    schedule_id: Optional[int] = Field(default=None, primary_key=True)
    course_id: int = Field(
        foreign_key="course.course_id",
    )
    instructor_id: Optional[int] = Field(
        foreign_key="instructor.instructor_id",
    )
    room_id: Optional[int] = Field(
        foreign_key="room.room_id",
    )
    chapter: Optional[str] = Field(default=None)
    # day_of_week field removed
    schedule_date: date = Field()
    start_time: str = Field()
    end_time: str = Field()
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    instructor: Optional["Instructor"] = Relationship(back_populates="schedules")
    course: Optional["Course"] = Relationship(back_populates="schedules")
    room: Optional["Room"] = Relationship(back_populates="schedules")
    attendances: List["Attendance"] = Relationship(back_populates="schedule")
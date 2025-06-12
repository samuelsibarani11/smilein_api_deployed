from sqlmodel import SQLModel, Field, Relationship
from typing import TYPE_CHECKING, Optional, List
from datetime import datetime

if TYPE_CHECKING:
    from app.models.instructor_course import InstructorCourse
    from app.models.schedule import Schedule


class Course(SQLModel, table=True):
    course_id: Optional[int] = Field(default=None, primary_key=True)
    course_name: str = Field(max_length=100)
    sks: int = Field(gt=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    instructors: List["InstructorCourse"] = Relationship(back_populates="course")
    schedules: Optional[List["Schedule"]] = Relationship(back_populates="course")

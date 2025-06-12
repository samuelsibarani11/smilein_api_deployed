from sqlmodel import SQLModel, Field, Relationship
from typing import TYPE_CHECKING, Optional, List
from datetime import datetime

if TYPE_CHECKING:
    from app.models.instructor_course import InstructorCourse
    from app.models.schedule import Schedule


class Instructor(SQLModel, table=True):
    instructor_id: Optional[int] = Field(default=None, primary_key=True)
    nidn: str = Field()
    full_name: str = Field(max_length=100)
    username: str = Field(unique=True, index=True, max_length=50)
    password: str = Field()
    email: str = Field()
    phone_number: str = Field()
    profile_picture_url: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    courses: List["InstructorCourse"] = Relationship(back_populates="instructor")
    schedules: List["Schedule"] = Relationship(back_populates="instructor")

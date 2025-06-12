from sqlmodel import SQLModel, Field, Relationship
from typing import TYPE_CHECKING, Optional
from datetime import datetime

if TYPE_CHECKING:
    from app.models.instructor import Instructor
    from app.models.course import Course


class InstructorCourse(SQLModel, table=True):
    instructor_course_id: Optional[int] = Field(default=None, primary_key=True)
    instructor_id: int = Field(
        foreign_key="instructor.instructor_id", ondelete="CASCADE"
    )
    course_id: int = Field(foreign_key="course.course_id", ondelete="CASCADE")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    instructor: Optional["Instructor"] = Relationship(back_populates="courses")
    course: Optional["Course"] = Relationship(back_populates="instructors")

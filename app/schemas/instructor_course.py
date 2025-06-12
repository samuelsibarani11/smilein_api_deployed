from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

from app.schemas.course import CourseBase
from app.schemas.instructor import InstructorBase

class InstructorCourseBase(BaseModel):
    instructor_id: int
    course_id: int

class InstructorCourseCreate(InstructorCourseBase):
    pass

class InstructorCourseUpdate(BaseModel):
    instructor_id: Optional[int] = None
    course_id: Optional[int] = None

class InstructorCourseRead(InstructorCourseBase):
    instructor_course_id: int
    instructor_id: int
    course_id: int
    created_at: datetime
    instructor: Optional[InstructorBase] = None
    course: Optional[CourseBase] = None

    model_config = ConfigDict(from_attributes=True)
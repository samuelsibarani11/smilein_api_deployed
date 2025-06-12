from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime


class CourseBase(BaseModel):
    course_name: str = Field(max_length=100)
    sks: int = Field(gt=0)


class CourseCreate(CourseBase):
    pass


class CourseUpdate(CourseBase):
    pass


class CourseRead(CourseBase):
    course_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CourseResponse(BaseModel):
    course_id: int
    course_name: Optional[str] = None


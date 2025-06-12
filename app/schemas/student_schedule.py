from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

from app.schemas.schedule import ScheduleRead
from app.schemas.student import StudentRead

class StudentScheduleBase(BaseModel):
    student_id: int
    schedule_id: int

class StudentScheduleCreate(StudentScheduleBase):
    pass

class StudentScheduleUpdate(BaseModel):
    student_id: Optional[int] = None
    schedule_id: Optional[int] = None

class StudentScheduleRead(BaseModel):
    student_schedule_id: int
    student_id: int
    schedule_id: int
    created_at: datetime
    student: StudentRead
    schedule: ScheduleRead

    model_config = ConfigDict(from_attributes=True)
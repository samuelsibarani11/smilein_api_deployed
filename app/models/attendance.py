from sqlmodel import JSON, Column, SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from app.models.student import Student
    from app.models.schedule import Schedule


class Attendance(SQLModel, table=True):
    attendance_id: Optional[int] = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="student.student_id", ondelete="CASCADE")
    schedule_id: int = Field(foreign_key="schedule.schedule_id", ondelete="CASCADE")
    date: datetime = Field()
    check_in_time: Optional[datetime] = Field(default=None)
    status: str = Field(regex="^(PRESENT|LATE|ABSENT|ON_GOING)$")
    location_data: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    face_verification_data: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    smile_detected: bool = Field(default=False)
    image_captured_url: Optional[str] = Field(default=None)  
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)

    student: Optional["Student"] = Relationship(back_populates="attendances")
    schedule: Optional["Schedule"] = Relationship(back_populates="attendances")
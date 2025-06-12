from sqlmodel import JSON, Column, SQLModel, Field, Relationship
from typing import TYPE_CHECKING, Optional, List
from datetime import datetime

if TYPE_CHECKING:
    from app.models.attendance import Attendance
    from app.models.schedule import Schedule


class Student(SQLModel, table=True):
    student_id: Optional[int] = Field(default=None, primary_key=True)
    nim: str = Field(unique=True, index=True, max_length=20)  # Adding NIM field
    username: str = Field(unique=True, index=True, max_length=50)
    password: str = Field()
    full_name: str = Field(max_length=100)
    major_name: str = Field(max_length=100)
    profile_picture_url: Optional[str] = Field(default=None)
    face_data: dict = Field(default_factory=dict, sa_column=Column(JSON))
    year: str = Field(regex="^[0-9]{4}/[0-9]{4}$")
    is_approved: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    attendances: List["Attendance"] = Relationship(back_populates="student")

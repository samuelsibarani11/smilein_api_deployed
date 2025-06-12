from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class InstructorBase(BaseModel):
    nidn: str = Field(max_length=20)
    full_name: str = Field(max_length=100)
    username: str = Field(max_length=50)
    email: str = Field(max_length=20)
    phone_number: str = Field(max_length=15)
    profile_picture_url: Optional[str] = None


class InstructorLogin(BaseModel):
    username: str
    password: str


class InstructorCreate(InstructorBase):
    password: str


class InstructorUpdate(InstructorBase):
    password: Optional[str] = None


class InstructorRead(InstructorBase):
    instructor_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InstructorResponse(BaseModel):
    instructor_id: int
    full_name: Optional[str] = None

# Add this to app/schemas/instructor.py
class InstructorChangePassword(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str
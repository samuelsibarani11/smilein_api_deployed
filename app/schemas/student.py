from typing import Optional, Dict
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime


class StudentBase(BaseModel):
    nim: str = Field(max_length=20)  # Adding NIM field
    username: str = Field(max_length=50)
    full_name: str = Field(max_length=100)
    major_name: str = Field(max_length=100)
    profile_picture_url: Optional[str] = None
    face_data: Optional[Dict] = None
    year: str = Field(pattern="^[0-9]{4}/[0-9]{4}$")
    is_approved: bool = False


class StudentCreate(StudentBase):
    password: str


class StudentUpdate(BaseModel):
    nim: Optional[str] = None  # Adding NIM field
    full_name: Optional[str] = None
    major_name: Optional[str] = None
    profile_picture_url: Optional[str] = None
    face_data: Optional[Dict] = None
    year: Optional[str] = Field(pattern="^[0-9]{4}/[0-9]{4}$")
    is_approved: Optional[bool] = None
    password: Optional[str] = None


class StudentRead(StudentBase):
    student_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StudentLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class StudentResponse(BaseModel):
    student_id: int
    nim: str  # Adding NIM field
    full_name: Optional[str] = None

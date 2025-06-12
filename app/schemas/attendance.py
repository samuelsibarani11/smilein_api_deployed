from datetime import date, datetime
from typing import Optional, Dict, Any, Union, List
from pydantic import BaseModel, validator
from sqlmodel import SQLModel
import json

from app.schemas.schedule import ScheduleRead
from app.schemas.student import StudentBase


class AttendanceBase(BaseModel):
    student_id: int  # Required for admin to create attendance record
    schedule_id: int  # Required for admin to create attendance record


class AttendanceCreate(AttendanceBase):
    # Only need student_id and schedule_id for creation
    # All other fields will be populated during check-in
    pass


class MultipleAttendanceCreate(BaseModel):
    """
    Schema for creating multiple attendance records at once for a single schedule
    """

    student_ids: List[int]  
    schedule_id: int  
    

class AttendanceCheckIn(BaseModel):
    # For students to check in - all fields are optional
    check_in_time: Optional[datetime] = None  # If None, current time will be used
    location_data: Optional[Union[Dict[str, Any], str]] = None
    face_verification_data: Optional[Union[Dict[str, Any], str]] = None
    smile_detected: Optional[bool] = False
    image_captured_url: Optional[str] = None  # Add image captured field (base64 string)

    @validator("location_data", "face_verification_data", pre=True)
    def parse_json_string(cls, value):
        if value is None:
            return None
        
        if isinstance(value, (str, int, float)):
            try:
                if isinstance(value, (int, float)):
                    # Convert numeric values to string
                    return {"data": str(value)}
                return json.loads(value)
            except json.JSONDecodeError:
                return {"data": str(value)}
        
        return value


class AttendanceRead(SQLModel):
    attendance_id: int
    student_id: int
    schedule_id: int
    date: date
    check_in_time: Optional[datetime]
    status: str  
    location_data: Optional[Dict[str, Any]]
    face_verification_data: Optional[Dict[str, Any]]
    smile_detected: bool
    image_captured_url: Optional[str] = None  
    created_at: datetime
    updated_at: Optional[datetime] = None

    @validator("location_data", "face_verification_data", pre=True)
    def ensure_dict(cls, value):
        if value is None:
            return None

        if isinstance(value, dict):
            return value

        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return {"data": value}

        return {"data": str(value)}

    class Config:
        from_attributes = True


class AttendanceUpdate(BaseModel):
    status: Optional[str] = None
    updated_at: Optional[datetime] = None
    location_data: Optional[Dict[str, Any]] = None
    face_verification_data: Optional[Dict[str, Any]] = None
    image_captured_url: Optional[str] = None  # Added field for image captured

    @validator("location_data", "face_verification_data", pre=True)
    def parse_json_string(cls, value):
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return {"data": value}
        return value


class AttendanceWithScheduleRead(AttendanceRead):
    # Student related fields
    student_name: Optional[str] = None
    student_email: Optional[str] = None
    student_nim: Optional[str] = None
    student_phone: Optional[str] = None
    student_address: Optional[str] = None
    # Add any other student fields you want to include

    # Schedule related fields
    schedule_day: Optional[str] = None
    schedule_time: Optional[str] = None
    schedule_start_time: Optional[str] = None
    schedule_end_time: Optional[str] = None
    schedule_day_of_week: Optional[int] = None

    # Room related fields
    room_id: Optional[int] = None
    room_name: Optional[str] = None
    room_latitude: Optional[float] = None
    room_longitude: Optional[float] = None
    room_radius: Optional[float] = None
    room_building: Optional[str] = None
    room_floor: Optional[str] = None

    # Course related fields
    course_id: Optional[int] = None
    course_name: Optional[str] = None
    course_code: Optional[str] = None
    course_credits: Optional[int] = None
    course_description: Optional[str] = None

    # Instructor related fields
    instructor_id: Optional[int] = None
    instructor_name: Optional[str] = None
    instructor_email: Optional[str] = None

    class Config:
        from_attributes = True


class MultipleAttendanceDelete(BaseModel):
    """
    Schema for deleting multiple attendance records at once
    """

    attendance_ids: List[int]


class AttendanceWithNestedData(BaseModel):
    attendance_id: int
    date: date
    check_in_time: Optional[datetime] = None
    status: str
    location_data: Optional[Dict[str, Any]] = None
    face_verification_data: Optional[Dict[str, Any]] = None
    smile_detected: bool
    image_captured_url: Optional[str] = None  # Added field for image captured
    created_at: datetime
    updated_at: Optional[datetime] = None

    # Nested objects
    student: StudentBase
    schedule: ScheduleRead

    class Config:
        # orm_mode = True
        from_attributes = True

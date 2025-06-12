from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class AdminBase(BaseModel):
    full_name: str = Field(max_length=100)
    username: str = Field(max_length=50)
    profile_picture_url: Optional[str] = None


class AdminCreate(AdminBase):
    password: str


class AdminLogin(BaseModel):
    username: str
    password: str


class AdminUpdate(AdminBase):
    password: Optional[str] = None


class AdminRead(AdminBase):
    admin_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Add this to app/schemas/admin.py
class AdminChangePassword(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class Admin(SQLModel, table=True):
    admin_id: Optional[int] = Field(default=None, primary_key=True)
    full_name: str = Field(max_length=100)
    username: str = Field(unique=True, index=True, max_length=50)
    password: str = Field()
    profile_picture_url: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
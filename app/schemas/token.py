# app/schemas/token.py

from typing import Optional
from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str
    user_type: str
    user_id: int


class TokenData(BaseModel):
    username: Optional[str] = None
    user_type: Optional[str] = None
    user_id: Optional[int] = None



from typing import Optional, Tuple
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from jose import jwt
from passlib.context import CryptContext
from sqlmodel import Session
import os
from dotenv import load_dotenv

from app.utils.time_utils import get_indonesia_time

load_dotenv()

# Constants
SECRET_KEY = os.getenv("SECRET_KEY", "default-fallback-key")
ALGORITHM = "HS256"

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate a password hash."""
    return pwd_context.hash(password)


def authenticate(db: Session, username: str, password: str) -> Tuple[object, str]:
    """
    Unified authentication that tries both student and instructor tables.
    Returns a tuple of (user_object, user_type).
    """
    # Import here to avoid circular imports
    from app.models.student import Student
    from app.models.instructor import Instructor
    from app.models.admin import Admin

    # First try student
    student = db.query(Student).filter(Student.username == username).first()
    if student and verify_password(password, student.password):
        return student, "student"

    # Then try instructor
    instructor = db.query(Instructor).filter(Instructor.username == username).first()
    if instructor and verify_password(password, instructor.password):
        return instructor, "instructor"

    # Then try admin
    admin = db.query(Admin).filter(Admin.username == username).first()
    if admin and verify_password(password, admin.password):
        return admin, "admin"

    # If both fail, raise exception
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )


# Keep these for backward compatibility
def authenticate_user(db: Session, username: str, password: str):
    """Authenticate a user by username and password."""
    user, user_type = authenticate(db, username, password)
    if user_type != "student":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not a student account",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def authenticate_instructor(db: Session, username: str, password: str):
    """Authenticate an instructor by username and password."""
    user, user_type = authenticate(db, username, password)
    if user_type != "instructor":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not an instructor account",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def authenticate_admin(db: Session, username: str, password: str):
    """Authenticate an instructor by username and password."""
    user, user_type = authenticate(db, username, password)
    if user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not an admin account",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
    user_type: str = None,
    user_id: int = None,
):
    """Create a JWT access token with user type and ID."""
    to_encode = data.copy()

    if expires_delta:
        expire = get_indonesia_time() + expires_delta
    else:
        expire = get_indonesia_time() + timedelta(minutes=15)

    to_encode.update({"exp": expire})
    if user_type:
        to_encode.update({"user_type": user_type})
    if user_id:
        to_encode.update({"user_id": user_id})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt

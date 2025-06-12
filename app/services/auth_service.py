# app/services/auth_service.py

from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Union

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlmodel import Session

from app.schemas.token import Token, TokenData
from app.utils.authentication import (
    SECRET_KEY,
    ALGORITHM,
    authenticate,
    verify_password,
    get_password_hash,
    create_access_token,
)
from app.dependencies import get_db
from app.models.student import Student
from app.models.instructor import Instructor
from app.models.admin import Admin
from app.utils.time_utils import get_indonesia_time

# OAuth2 configuration
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

# Constants
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def login_user(db: Session, username: str, password: str) -> Dict[str, str]:
    """
    Authenticates a user and returns an access token.
    Works for students, instructors, and admins.
    """
    try:
        user, user_type = authenticate(db, username, password)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Determine user ID field based on user type
    user_id_field = f"{user_type}_id"
    user_id = getattr(user, user_id_field, None)

    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": username},
        expires_delta=access_token_expires,
        user_type=user_type,
        user_id=user_id,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_type": user_type,
        "user_id": user_id,
    }


def get_current_user_data(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> Dict[str, Union[Student, Instructor, Admin, str]]:
    """
    Validates the token and returns the user data including the user type.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_type: str = payload.get("user_type")
        user_id: int = payload.get("user_id")

        if username is None or user_type is None or user_id is None:
            raise credentials_exception

        token_data = TokenData(username=username, user_type=user_type, user_id=user_id)
    except JWTError:
        raise credentials_exception

    # Get the appropriate user based on user_type
    if token_data.user_type == "student":
        user = db.get(Student, token_data.user_id)
    elif token_data.user_type == "instructor":
        user = db.get(Instructor, token_data.user_id)
    elif token_data.user_type == "admin":
        user = db.get(Admin, token_data.user_id)
    else:
        raise credentials_exception

    if user is None:
        raise credentials_exception

    return {"user": user, "user_type": token_data.user_type}


def get_current_user(
    current_user_data: dict = Depends(get_current_user_data),
) -> Union[Student, Instructor, Admin]:
    """
    Returns just the user object from the current_user_data.
    """
    return current_user_data["user"]


def get_current_student(
    current_user_data: dict = Depends(get_current_user_data),
) -> Student:
    """
    Verifies that the current user is a student and returns the student object.
    """
    if current_user_data["user_type"] != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized as student",
        )
    return current_user_data["user"]


def get_current_instructor(
    current_user_data: dict = Depends(get_current_user_data),
) -> Instructor:
    """
    Verifies that the current user is an instructor and returns the instructor object.
    """
    if current_user_data["user_type"] != "instructor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized as instructor",
        )
    return current_user_data["user"]


def get_current_admin(
    current_user_data: dict = Depends(get_current_user_data),
) -> Admin:
    """
    Verifies that the current user is an admin and returns the admin object.
    """
    if current_user_data["user_type"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized as admin",
        )
    return current_user_data["user"]


def change_password(
    db: Session, user_type: str, user_id: int, current_password: str, new_password: str
) -> bool:
    """
    Changes a user's password after verifying the current password.
    Works for students, instructors, and admins.
    """
    if user_type == "student":
        user = db.get(Student, user_id)
    elif user_type == "instructor":
        user = db.get(Instructor, user_id)
    elif user_type == "admin":
        user = db.get(Admin, user_id)
    else:
        return False

    if user is None:
        return False

    # Verify current password
    if not verify_password(current_password, user.password):
        return False

    # Update password
    user.password = get_password_hash(new_password)
    user.updated_at = get_indonesia_time()

    db.add(user)
    db.commit()
    db.refresh(user)

    return True

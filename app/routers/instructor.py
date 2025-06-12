import os
from datetime import datetime
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlmodel import Session
from typing import List

from app.dependencies import (
    get_current_user_data,
    get_db,
    instructor_access_from_path,
    get_current_admin_or_instructor,
)
from app.schemas.instructor import (
    InstructorChangePassword,
    InstructorCreate,
    InstructorRead,
    InstructorUpdate,
)
from app.crud.instructor import (
    change_instructor_password,
    create_instructor,
    get_instructors,
    get_instructor,
    get_instructor_by_username,
    get_next_instructor,
    update_instructor,
    delete_instructor,
)
from app.utils.time_utils import get_indonesia_time


router = APIRouter(
    prefix="/instructors",
    tags=["instructors"],
    responses={404: {"description": "Not found"}},
)


@router.post("/", response_model=InstructorRead, status_code=status.HTTP_201_CREATED)
def create_instructor_endpoint(
    instructor: InstructorCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new instructor account.

    This endpoint allows the creation of new instructor accounts in the system.
    It validates that the username is unique before creating the account and
    automatically generates necessary instructor credentials and settings.

    Args:
        instructor: Instructor creation data including username, email, and profile info
        db: Database session dependency

    Returns:
        InstructorRead: The newly created instructor with generated ID

    Raises:
        HTTPException: 400 if username already exists

    Access Level: PUBLIC (registration endpoint)
    """
    db_instructor = get_instructor_by_username(db, username=instructor.username)
    if db_instructor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )
    return create_instructor(db=db, instructor=instructor)


@router.get("/", response_model=List[InstructorRead])
def read_instructors_endpoint(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin_or_instructor),
):
    """
    Retrieve instructors with role-based filtering.

    This endpoint returns instructor information based on user permissions:
    - Admins can view all instructors in the system
    - Instructors can only view their own profile information

    Args:
        skip: Number of records to skip for pagination (default: 0)
        limit: Maximum number of records to return (default: 100)
        db: Database session dependency
        current_user: Current authenticated user with role information

    Returns:
        List[InstructorRead]: List of instructors accessible to current user

    Access Level: ADMIN | INSTRUCTOR
    """
    user = current_user["user"]
    user_type = current_user["user_type"]

    if user_type == "admin":
        instructors = get_instructors(db, skip=skip, limit=limit)
    else:
        instructors = [get_instructor(db, instructor_id=user.instructor_id)]

    return instructors


@router.get("/{instructor_id}", response_model=InstructorRead)
def read_instructor_endpoint(
    instructor_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(instructor_access_from_path()),
):
    """
    Retrieve a specific instructor's profile information.

    This endpoint allows authorized users to fetch detailed information about
    a specific instructor. Access is granted to admins and the instructor
    themselves for their own profile.

    Args:
        instructor_id: Unique identifier of the instructor to retrieve
        db: Database session dependency
        current_user: Current authenticated user with instructor access validation

    Returns:
        InstructorRead: Detailed instructor profile information

    Raises:
        HTTPException: 404 if instructor is not found

    Access Level: ADMIN | INSTRUCTOR (own profile only)
    """
    instructor = get_instructor(db, instructor_id=instructor_id)
    if instructor is None:
        raise HTTPException(status_code=404, detail="Instructor not found")
    return instructor


@router.patch("/{instructor_id}", response_model=InstructorRead)
def update_instructor_endpoint(
    instructor_id: int,
    instructor: InstructorUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(instructor_access_from_path()),
):
    """
    Update an instructor's profile information.

    This endpoint allows authorized users to modify instructor profile data
    such as personal information, contact details, and other editable fields.
    Access is restricted to admins and the instructor themselves.

    Args:
        instructor_id: Unique identifier of the instructor to update
        instructor: Updated profile data with modified fields
        db: Database session dependency
        current_user: Current authenticated user with instructor access validation

    Returns:
        InstructorRead: The updated instructor profile information

    Raises:
        HTTPException: 404 if instructor is not found

    Access Level: ADMIN | INSTRUCTOR (own profile only)
    """
    db_instructor = update_instructor(
        db, instructor_id=instructor_id, instructor=instructor
    )
    if db_instructor is None:
        raise HTTPException(status_code=404, detail="Instructor not found")
    return db_instructor


@router.delete("/{instructor_id}")
def delete_instructor_endpoint(
    instructor_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(instructor_access_from_path()),
):
    """
    Delete an instructor account from the system.

    This endpoint allows authorized users to permanently remove an instructor
    account and all associated data. This action should be used carefully as
    it may affect course assignments and student relationships.

    Args:
        instructor_id: Unique identifier of the instructor to delete
        db: Database session dependency
        current_user: Current authenticated user with instructor access validation

    Returns:
        dict: Success message confirming deletion

    Raises:
        HTTPException: 404 if instructor is not found

    Access Level: ADMIN | INSTRUCTOR (own profile only)
    """
    success = delete_instructor(db, instructor_id=instructor_id)
    if not success:
        raise HTTPException(status_code=404, detail="Instructor not found")
    return {"message": "Instructor successfully deleted"}


@router.get("/{instructor_id}/next", response_model=InstructorRead)
def get_next_instructor_endpoint(
    instructor_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin_or_instructor),
):
    """
    Get the next instructor in sequence by ID order.

    This endpoint is useful for navigation purposes, allowing users to browse
    through instructor profiles sequentially. It returns the instructor with
    the next higher ID in the database.

    Args:
        instructor_id: Current instructor ID to find the next one from
        db: Database session dependency
        current_user: Current authenticated user

    Returns:
        InstructorRead: The next instructor profile in sequence

    Raises:
        HTTPException: 404 if current instructor not found or no next instructor exists

    Access Level: ADMIN | INSTRUCTOR
    """
    current_instructor = get_instructor(db, instructor_id=instructor_id)
    if current_instructor is None:
        raise HTTPException(status_code=404, detail="Current instructor not found")

    next_instructor = get_next_instructor(db, current_instructor_id=instructor_id)
    if next_instructor is None:
        raise HTTPException(status_code=404, detail="No other instructors found")

    return next_instructor


@router.post("/{instructor_id}/profile-picture", response_model=InstructorRead)
async def upload_instructor_profile_picture_endpoint(
    instructor_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user_data=Depends(get_current_user_data),
):
    """
    Upload and update an instructor's profile picture.

    This endpoint handles profile picture uploads with validation for file type
    and user permissions. It automatically manages old file cleanup and generates
    timestamped filenames to prevent conflicts. Only admins or the instructor
    themselves can update profile pictures.

    Args:
        instructor_id: Unique identifier of the instructor
        file: Uploaded image file (JPEG, PNG, or GIF)
        db: Database session dependency
        current_user_data: Current authenticated user data with role information

    Returns:
        InstructorRead: Updated instructor profile with new picture URL

    Raises:
        HTTPException: 403 if unauthorized, 404 if instructor not found, 400 if invalid file

    Access Level: ADMIN | INSTRUCTOR (own profile only)
    """
    user = current_user_data["user"]
    user_type = current_user_data["user_type"]

    is_admin = user_type == "admin"
    is_same_instructor = (
        user_type == "instructor" and user.instructor_id == instructor_id
    )

    if not is_admin and not is_same_instructor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only modify your own profile picture or you need admin privileges",
        )

    db_instructor = get_instructor(db, instructor_id=instructor_id)
    if db_instructor is None:
        raise HTTPException(status_code=404, detail="Instructor not found")

    valid_content_types = ["image/jpeg", "image/png", "image/gif", "image/jpg"]
    if file.content_type not in valid_content_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image (JPEG, PNG, or GIF)",
        )

    upload_dir = "uploads/instructor_profile_pictures"
    os.makedirs(upload_dir, exist_ok=True)

    if db_instructor.profile_picture_url:
        old_file_path = db_instructor.profile_picture_url.replace(
            "/uploads/", "uploads/"
        )
        if os.path.exists(old_file_path):
            os.remove(old_file_path)

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    file_extension = os.path.splitext(file.filename)[1]
    filename = f"instructor_{instructor_id}_{timestamp}{file_extension}"
    file_path = os.path.join(upload_dir, filename)

    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    profile_picture_url = f"/uploads/instructor_profile_pictures/{filename}"
    db_instructor.profile_picture_url = profile_picture_url
    db_instructor.updated_at = get_indonesia_time()
    db.add(db_instructor)
    db.commit()
    db.refresh(db_instructor)

    return db_instructor


@router.post("/change-password")
def change_password_endpoint(
    password_data: InstructorChangePassword,
    db: Session = Depends(get_db),
    current_user_data=Depends(get_current_user_data),
):
    """
    Change an instructor's account password.

    This endpoint allows instructors to securely change their account passwords
    by providing their current password and confirming the new password. It
    validates the current password and ensures the new password confirmation
    matches before updating the account.

    Args:
        password_data: Password change data including current and new passwords
        db: Database session dependency
        current_user_data: Current authenticated user data

    Returns:
        dict: Success message confirming password change

    Raises:
        HTTPException: 403 if not instructor, 400 if validation fails, 404 if instructor not found

    Access Level: INSTRUCTOR only
    """
    user = current_user_data["user"]
    user_type = current_user_data["user_type"]

    if user_type != "instructor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only instructors can perform this action",
        )

    if password_data.new_password != password_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password and confirmation do not match",
        )

    result = change_instructor_password(
        db=db,
        instructor_id=user.instructor_id,
        current_password=password_data.current_password,
        new_password=password_data.new_password,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Instructor not found"
        )
    elif result is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    return {"message": "Password successfully changed"}


@router.get("/{instructor_id}/profile-picture")
def get_instructor_profile_picture_endpoint(
    instructor_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin_or_instructor),
):
    """
    Retrieve an instructor's profile picture URL.

    This endpoint returns the URL of an instructor's profile picture if one
    has been uploaded. It's useful for displaying profile images in the
    frontend application or for verification purposes.

    Args:
        instructor_id: Unique identifier of the instructor
        db: Database session dependency
        current_user: Current authenticated user

    Returns:
        dict: Profile picture URL information

    Raises:
        HTTPException: 404 if instructor or profile picture not found

    Access Level: ADMIN | INSTRUCTOR
    """
    instructor = get_instructor(db, instructor_id=instructor_id)
    if instructor is None:
        raise HTTPException(status_code=404, detail="Instructor not found")

    if not instructor.profile_picture_url:
        raise HTTPException(status_code=404, detail="Profile picture not found")

    return {"profile_picture_url": instructor.profile_picture_url}

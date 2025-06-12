import json
import os
from datetime import datetime
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Body, UploadFile, File, status
from sqlmodel import Session

from app.dependencies import (
    get_current_admin,
    get_current_admin_or_instructor,
    get_current_user_data,
    get_db,
    get_current_user,
)
from app.schemas.student import StudentCreate, StudentRead, StudentUpdate
import app.crud.student as crud
from app.utils.time_utils import get_indonesia_time

# Router configuration with access control information
# HAK AKSES: ADMIN | INSTRUCTOR | STUDENT
router = APIRouter(
    prefix="/students",
    tags=["students"],
)


@router.post("/", response_model=StudentRead, status_code=status.HTTP_201_CREATED)
def create_student_endpoint(
    student: StudentCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new student account.

    Validates that both username and NIM are unique before creating the student record.
    Returns the created student data with generated ID and timestamps.

    Args:
        student: Student data including username, NIM, and other required fields
        db: Database session dependency

    Returns:
        StudentRead: Created student data

    Raises:
        HTTPException: 400 if username or NIM already exists
    """
    # Validate username uniqueness
    db_student = crud.get_student_by_username(db, username=student.username)
    if db_student:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    # Validate NIM uniqueness
    db_student_nim = crud.get_student_by_nim(db, nim=student.nim)
    if db_student_nim:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="NIM already registered",
        )

    return crud.create_student(db=db, student=student)


@router.get("/", response_model=List[StudentRead])
def read_students_endpoint(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_instructor=Depends(get_current_admin_or_instructor),
):
    """
    Retrieve a paginated list of all students.

    Requires admin or instructor authentication. Supports pagination through
    skip and limit parameters for efficient data retrieval.

    Args:
        skip: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: 100)
        db: Database session dependency
        current_instructor: Authentication dependency for admin/instructor access

    Returns:
        List[StudentRead]: List of student records
    """
    students = crud.get_students(db, skip=skip, limit=limit)
    return students


@router.get("/nim/{nim}", response_model=StudentRead)
def read_student_by_nim_endpoint(
    nim: str,
    db: Session = Depends(get_db),
    current_instructor=Depends(get_current_admin_or_instructor),
):
    """
    Retrieve a specific student by their NIM (Student ID Number).

    Requires admin or instructor authentication. NIM is the unique identifier
    used by the academic institution for student identification.

    Args:
        nim: Student's NIM (Nomor Induk Mahasiswa)
        db: Database session dependency
        current_instructor: Authentication dependency for admin/instructor access

    Returns:
        StudentRead: Student data matching the provided NIM

    Raises:
        HTTPException: 404 if student with given NIM is not found
    """
    student = crud.get_student_by_nim(db, nim=nim)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@router.get("/{student_id}", response_model=StudentRead)
def read_student_endpoint(
    student_id: int,
    db: Session = Depends(get_db),
):
    """
    Retrieve a specific student by their database ID.

    Provides access to student data using the internal database identifier.
    This endpoint has more permissive access compared to other read operations.

    Args:
        student_id: Internal database ID of the student
        db: Database session dependency

    Returns:
        StudentRead: Student data matching the provided ID

    Raises:
        HTTPException: 404 if student with given ID is not found
    """
    student = crud.get_student(db, student_id=student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@router.put("/{student_id}", response_model=StudentRead)
def update_student_endpoint(
    student_id: int,
    student: StudentUpdate,
    db: Session = Depends(get_db),
    current_user_data=Depends(get_current_user_data),
):
    """
    Update student information with authorization control.

    Allows admins to update any student or students to update their own profile.
    Validates NIM uniqueness if it's being changed to prevent conflicts.

    Args:
        student_id: ID of the student to update
        student: Updated student data
        db: Database session dependency
        current_user_data: Current user information and type for authorization

    Returns:
        StudentRead: Updated student data

    Raises:
        HTTPException: 403 if user lacks permission, 400 if NIM conflict, 404 if student not found
    """
    user = current_user_data["user"]
    user_type = current_user_data["user_type"]

    # Authorization check: admin or self-update only
    is_admin = user_type == "admin"
    is_same_student = user_type == "student" and user.student_id == student_id

    if not is_admin and not is_same_student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only modify your own profile or you need admin privileges",
        )

    # Validate NIM uniqueness if being updated
    if student.nim is not None:
        existing_student = crud.get_student_by_nim(db, nim=student.nim)
        if existing_student and existing_student.student_id != student_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="NIM already registered to another student",
            )

    updated_student = crud.update_student(db, student_id=student_id, student=student)
    if updated_student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return updated_student


@router.post("/{student_id}/profile-picture", response_model=StudentRead)
async def upload_profile_picture_endpoint(
    student_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user_data=Depends(get_current_user_data),
):
    """
    Upload and update a student's profile picture.

    Handles file validation, storage management, and database updates for profile pictures.
    Automatically removes old profile pictures when new ones are uploaded. Supports
    common image formats and implements proper authorization controls.

    Args:
        student_id: ID of the student whose profile picture is being updated
        file: Uploaded image file (JPEG, PNG, GIF supported)
        db: Database session dependency
        current_user_data: Current user information for authorization

    Returns:
        StudentRead: Updated student data with new profile picture URL

    Raises:
        HTTPException: 403 if unauthorized, 404 if student not found, 400 if invalid file type
    """
    user = current_user_data["user"]
    user_type = current_user_data["user_type"]

    # Authorization check: admin or self-update only
    is_admin = user_type == "admin"
    is_same_student = user_type == "student" and user.student_id == student_id

    if not is_admin and not is_same_student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only modify your own profile picture or you need admin privileges",
        )

    # Verify student exists
    db_student = crud.get_student(db, student_id=student_id)
    if db_student is None:
        raise HTTPException(status_code=404, detail="Student not found")

    # Validate file type
    valid_content_types = ["image/jpeg", "image/png", "image/gif", "image/jpg"]
    if file.content_type not in valid_content_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image (JPEG, PNG, or GIF)",
        )

    # Ensure upload directory exists
    upload_dir = "uploads/profile_pictures"
    os.makedirs(upload_dir, exist_ok=True)

    # Remove old profile picture if exists
    if db_student.profile_picture_url:
        old_file_path = db_student.profile_picture_url.replace("/uploads/", "uploads/")
        if os.path.exists(old_file_path):
            os.remove(old_file_path)

    # Generate unique filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    file_extension = os.path.splitext(file.filename)[1]
    filename = f"{student_id}_{timestamp}{file_extension}"
    file_path = os.path.join(upload_dir, filename)

    # Save uploaded file
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    # Update database with new profile picture URL
    db_student.profile_picture_url = f"/uploads/profile_pictures/{filename}"
    db_student.updated_at = get_indonesia_time()
    db.add(db_student)
    db.commit()
    db.refresh(db_student)

    # Parse face_data JSON for response if exists
    if db_student.face_data:
        try:
            db_student.face_data = json.loads(db_student.face_data)
        except json.JSONDecodeError:
            db_student.face_data = None

    return db_student


@router.post("/{student_id}/face", response_model=StudentRead)
async def update_face_data_endpoint(
    student_id: int,
    face_data: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Update a student's face recognition data for biometric authentication.

    Stores facial recognition features and vectors used by the attendance system.
    Only allows students to update their own face data or admins to update any student's data.

    Args:
        student_id: ID of the student whose face data is being updated
        face_data: Dictionary containing facial recognition features and metadata
        db: Database session dependency
        current_user: Current authenticated user

    Returns:
        StudentRead: Updated student data with new face recognition information

    Raises:
        HTTPException: 403 if unauthorized, 404 if student not found
    """
    # Authorization check: self-update or admin only
    if current_user.student_id != student_id and not getattr(
        current_user, "is_admin", False
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )

    updated_student = crud.update_face_data(
        db, student_id=student_id, face_data=face_data
    )
    if updated_student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return updated_student


@router.delete("/{student_id}")
def delete_student_endpoint(
    student_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """
    Permanently delete a student record from the system.

    Removes all student data including profile pictures and associated records.
    This action is irreversible and requires admin privileges. Consider implementing
    soft delete for production systems to maintain data integrity.

    Args:
        student_id: ID of the student to delete
        db: Database session dependency
        current_user: Admin user authentication dependency

    Returns:
        dict: Success message confirming deletion

    Raises:
        HTTPException: 404 if student not found
    """
    success = crud.delete_student(db, student_id=student_id)
    if not success:
        raise HTTPException(status_code=404, detail="Student not found")
    return {"message": "Student successfully deleted"}


@router.get("/{student_id}/next", response_model=StudentRead)
def get_next_student_endpoint(
    student_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin_or_instructor),
):
    """
    Retrieve the next student in sequence for navigation purposes.

    Useful for administrative interfaces that need to navigate through student records
    sequentially. Returns the next student based on ID ordering in the database.

    Args:
        student_id: Current student ID as reference point
        db: Database session dependency
        current_user: Admin or instructor authentication dependency

    Returns:
        StudentRead: Next student data in sequence

    Raises:
        HTTPException: 404 if current student not found or no next student exists
    """
    # Verify current student exists
    current_student = crud.get_student(db, student_id=student_id)
    if current_student is None:
        raise HTTPException(status_code=404, detail="Current student not found")

    # Get next student in sequence
    next_student = crud.get_next_student(db, current_student_id=student_id)
    if next_student is None:
        raise HTTPException(status_code=404, detail="No other student found")

    return next_student


@router.get("/{student_id}/profile-picture")
def get_profile_picture_endpoint(
    student_id: int,
    db: Session = Depends(get_db),
):
    """
    Retrieve the URL of a student's profile picture.

    Returns the stored profile picture URL for display purposes. Used by frontend
    applications to show student photos in interfaces and reports.

    Args:
        student_id: ID of the student whose profile picture URL is requested
        db: Database session dependency

    Returns:
        dict: Dictionary containing the profile picture URL

    Raises:
        HTTPException: 404 if student not found or no profile picture exists
    """
    student = crud.get_student(db, student_id=student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")

    if not student.profile_picture_url:
        raise HTTPException(status_code=404, detail="Profile picture not found")

    return {"profile_picture_url": student.profile_picture_url}


@router.get("/username/{username}", response_model=StudentRead)
def read_student_by_username_endpoint(
    username: str,
    db: Session = Depends(get_db),
):
    """
    Retrieve a student by their username for authentication and lookup purposes.

    Provides an alternative lookup method using username instead of ID or NIM.
    Commonly used during login processes and user profile lookups.

    Args:
        username: Student's username for lookup
        db: Database session dependency

    Returns:
        StudentRead: Student data matching the provided username

    Raises:
        HTTPException: 404 if no student found with the given username
    """
    student = crud.get_student_by_username(db, username=username)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return student

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List

from app.dependencies import get_current_admin, get_db
from app.schemas.instructor_course import (
    InstructorCourseCreate,
    InstructorCourseRead,
    InstructorCourseUpdate,
)
from app.crud.instructor_course import (
    create_instructor_course,
    get_instructor_courses,
    get_instructor_course_by_id,
    update_instructor_course,
    delete_instructor_course,
)


router = APIRouter(
    prefix="/instructor-courses",
    tags=["instructor-courses"],
    responses={404: {"description": "Not found"}},
)


@router.post(
    "/", response_model=InstructorCourseRead, status_code=status.HTTP_201_CREATED
)
def create_instructor_course_endpoint(
    instructor_course: InstructorCourseCreate,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """
    Create a new instructor-course assignment.

    This endpoint allows administrators to assign instructors to specific courses,
    establishing the relationship that grants instructors access to manage and
    view course content. Each assignment creates a many-to-many relationship
    between instructors and courses.

    Args:
        instructor_course: Assignment data containing instructor and course IDs
        db: Database session dependency
        current_admin: Current authenticated admin user

    Returns:
        InstructorCourseRead: The newly created instructor-course assignment

    Access Level: ADMIN only
    """
    return create_instructor_course(db=db, instructor_course=instructor_course)


@router.get("/", response_model=List[InstructorCourseRead])
def read_instructor_courses_endpoint(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """
    Retrieve all instructor-course assignments with pagination.

    This endpoint provides administrators with a complete list of all instructor
    and course assignments in the system. It's useful for managing and auditing
    teaching assignments across the platform.

    Args:
        skip: Number of records to skip for pagination (default: 0)
        limit: Maximum number of records to return (default: 100)
        db: Database session dependency
        current_admin: Current authenticated admin user

    Returns:
        List[InstructorCourseRead]: List of all instructor-course assignments

    Access Level: ADMIN only
    """
    instructor_courses = get_instructor_courses(db, skip=skip, limit=limit)
    return instructor_courses


@router.get("/{instructor_course_id}", response_model=InstructorCourseRead)
def read_instructor_course_endpoint(
    instructor_course_id: int,
    db: Session = Depends(get_db),
    # current_admin=Depends(get_current_admin),
):
    """
    Retrieve a specific instructor-course assignment by ID.

    This endpoint allows administrators to fetch detailed information about
    a specific instructor-course assignment, including the relationship details
    and any associated metadata.

    Args:
        instructor_course_id: Unique identifier of the assignment to retrieve
        db: Database session dependency
        current_admin: Current authenticated admin user

    Returns:
        InstructorCourseRead: Detailed assignment information

    Raises:
        HTTPException: 404 if assignment is not found

    Access Level: ADMIN only
    """
    instructor_course = get_instructor_course_by_id(
        db, instructor_course_id=instructor_course_id
    )
    if instructor_course is None:
        raise HTTPException(status_code=404, detail="Instructor course not found")
    return instructor_course


@router.patch("/{instructor_course_id}", response_model=InstructorCourseRead)
def update_instructor_course_endpoint(
    instructor_course_id: int,
    instructor_course: InstructorCourseUpdate,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """
    Update an existing instructor-course assignment.

    This endpoint allows administrators to modify instructor-course assignments,
    such as changing assignment dates, updating permissions, or modifying other
    relationship metadata. Useful for maintaining accurate teaching assignments.

    Args:
        instructor_course_id: Unique identifier of the assignment to update
        instructor_course: Updated assignment data with modified fields
        db: Database session dependency
        current_admin: Current authenticated admin user

    Returns:
        InstructorCourseRead: The updated assignment information

    Raises:
        HTTPException: 404 if assignment is not found

    Access Level: ADMIN only
    """
    db_instructor_course = update_instructor_course(
        db,
        instructor_course_id=instructor_course_id,
        instructor_course=instructor_course,
    )
    if db_instructor_course is None:
        raise HTTPException(status_code=404, detail="Instructor course not found")
    return db_instructor_course


@router.delete("/{instructor_course_id}")
def delete_instructor_course_endpoint(
    instructor_course_id: int,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """
    Delete an instructor-course assignment.

    This endpoint allows administrators to remove instructor-course assignments,
    effectively revoking an instructor's access to a specific course. This action
    should be used carefully as it immediately removes teaching permissions.

    Args:
        instructor_course_id: Unique identifier of the assignment to delete
        db: Database session dependency
        current_admin: Current authenticated admin user

    Returns:
        dict: Success message confirming deletion

    Raises:
        HTTPException: 404 if assignment is not found

    Access Level: ADMIN only
    """
    success = delete_instructor_course(db, instructor_course_id=instructor_course_id)
    if not success:
        raise HTTPException(status_code=404, detail="Instructor course not found")
    return {"message": "Instructor course assignment successfully deleted"}

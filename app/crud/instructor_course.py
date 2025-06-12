from sqlmodel import Session
from fastapi import HTTPException, status
from sqlalchemy.orm import joinedload

from app.models.instructor_course import InstructorCourse
from app.schemas.instructor_course import InstructorCourseCreate, InstructorCourseUpdate
from app.utils.time_utils import get_indonesia_time


def create_instructor_course(
    db: Session, instructor_course: InstructorCourseCreate
) -> InstructorCourse:
    """
    Create a new instructor course assignment.

    Creates a new relationship between an instructor and a course with current timestamp.
    Validates the assignment data and commits to database.

    Args:
        db: Database session for transaction management
        instructor_course: Validated instructor course data from request

    Returns:
        InstructorCourse: Newly created instructor course assignment with generated ID

    Raises:
        SQLAlchemyError: If database operation fails
    """
    db_instructor_course = InstructorCourse(
        instructor_id=instructor_course.instructor_id,
        course_id=instructor_course.course_id,
        created_at=get_indonesia_time(),
    )
    db.add(db_instructor_course)
    db.commit()
    db.refresh(db_instructor_course)
    return db_instructor_course


def get_instructor_courses(
    db: Session, skip: int = 0, limit: int = 100
) -> list[InstructorCourse]:
    """
    Retrieve a paginated list of instructor course assignments.

    Fetches instructor course assignments with eager loading of related instructor
    and course data to minimize database queries. Supports pagination through
    skip and limit parameters.

    Args:
        db: Database session for query execution
        skip: Number of records to skip for pagination (default: 0)
        limit: Maximum number of records to return (default: 100)

    Returns:
        list[InstructorCourse]: List of instructor course assignments with related data
    """
    return (
        db.query(InstructorCourse)
        .options(
            joinedload(InstructorCourse.instructor), joinedload(InstructorCourse.course)
        )
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_instructor_course_by_id(
    db: Session, instructor_course_id: int
) -> InstructorCourse:
    """
    Retrieve a specific instructor course assignment by its ID.

    Fetches a single instructor course assignment using the provided ID.
    Raises HTTP 404 exception if the assignment is not found.

    Args:
        db: Database session for query execution
        instructor_course_id: Unique identifier of the instructor course assignment

    Returns:
        InstructorCourse: The requested instructor course assignment

    Raises:
        HTTPException: 404 error if instructor course assignment not found
    """
    instructor_course = db.get(InstructorCourse, instructor_course_id)
    if instructor_course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instructor course with ID {instructor_course_id} not found",
        )
    return instructor_course


def update_instructor_course(
    db: Session, instructor_course_id: int, instructor_course: InstructorCourseUpdate
) -> InstructorCourse:
    """
    Update an existing instructor course assignment.

    Updates only the provided fields in the instructor course assignment.
    Uses partial update strategy to avoid overwriting unchanged fields.
    Validates existence before attempting update.

    Args:
        db: Database session for transaction management
        instructor_course_id: ID of the assignment to update
        instructor_course: Updated assignment data (partial)

    Returns:
        InstructorCourse: Updated instructor course assignment

    Raises:
        HTTPException: 404 error if instructor course assignment not found
        SQLAlchemyError: If database operation fails
    """
    db_instructor_course = get_instructor_course_by_id(db, instructor_course_id)

    instructor_course_data = instructor_course.dict(exclude_unset=True)
    for key, value in instructor_course_data.items():
        setattr(db_instructor_course, key, value)

    db.add(db_instructor_course)
    db.commit()
    db.refresh(db_instructor_course)
    return db_instructor_course


def delete_instructor_course(
    db: Session, instructor_course_id: int
) -> InstructorCourse:
    """
    Delete an instructor course assignment by its ID.

    Removes the instructor course assignment from database after validating
    its existence. Returns the deleted assignment for confirmation or logging purposes.

    Args:
        db: Database session for transaction management
        instructor_course_id: ID of the assignment to delete

    Returns:
        InstructorCourse: The deleted instructor course assignment

    Raises:
        HTTPException: 404 error if instructor course assignment not found
        SQLAlchemyError: If database operation fails
    """
    db_instructor_course = get_instructor_course_by_id(db, instructor_course_id)
    db.delete(db_instructor_course)
    db.commit()
    return db_instructor_course

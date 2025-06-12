from fastapi import APIRouter, Depends, status, HTTPException
from sqlmodel import Session
from typing import List

from app.dependencies import (
    get_current_admin,
    get_current_admin_or_instructor,
    get_db,
    get_instructor_courses,
    course_access_from_path,
)
from app.schemas.course import CourseCreate, CourseUpdate, CourseRead
from app.crud.course import (
    get_courses,
    get_course_by_id,
    create_course,
    update_course,
    delete_course,
)


router = APIRouter(
    prefix="/courses",
    tags=["courses"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=List[CourseRead])
async def read_courses(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user_data=Depends(get_current_admin_or_instructor),
):
    """
    Retrieve courses with pagination based on user access level.

    This endpoint returns courses filtered by user permissions:
    - Admins can view all courses in the system
    - Instructors can only view courses they have been assigned to teach

    Args:
        skip: Number of records to skip for pagination (default: 0)
        limit: Maximum number of records to return (default: 100)
        db: Database session dependency
        current_user_data: Current authenticated user data with role information

    Returns:
        List[CourseRead]: List of courses accessible to the current user

    Access Level: ADMIN | INSTRUCTOR
    """
    user = current_user_data["user"]
    user_type = current_user_data["user_type"]

    if user_type == "admin":
        return get_courses(db, skip=skip, limit=limit)

    elif user_type == "instructor":
        accessible_course_ids = await get_instructor_courses(user.instructor_id, db)
        all_courses = get_courses(db, skip=skip, limit=limit)
        instructor_courses = [
            course
            for course in all_courses
            if course.course_id in accessible_course_ids
        ]
        return instructor_courses


@router.get("/{course_id}", response_model=CourseRead)
async def read_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(course_access_from_path()),
):
    """
    Retrieve a specific course by its ID.

    This endpoint allows authorized users to fetch detailed information about
    a specific course. Access is granted to admins and instructors who have
    been assigned to teach the course.

    Args:
        course_id: Unique identifier of the course to retrieve
        db: Database session dependency
        current_user: Current authenticated user with course access validation

    Returns:
        CourseRead: Detailed course information

    Raises:
        HTTPException: 404 if course is not found

    Access Level: ADMIN | INSTRUCTOR (with course access)
    """
    course = get_course_by_id(db, course_id=course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


@router.post("/", response_model=CourseRead, status_code=status.HTTP_201_CREATED)
def create_course_endpoint(
    course: CourseCreate,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """
    Create a new course in the system.

    This endpoint allows administrators to create new courses. After creation,
    instructors must be explicitly assigned to courses through the instructor_course
    relationship table to gain access to teach them.

    Args:
        course: Course creation data containing course details
        db: Database session dependency
        current_admin: Current authenticated admin user

    Returns:
        CourseRead: The newly created course with generated ID

    Access Level: ADMIN only
    """
    return create_course(db=db, course=course)


@router.put("/{course_id}", response_model=CourseRead)
async def update_course_endpoint(
    course_id: int,
    course: CourseUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(course_access_from_path()),
):
    """
    Update an existing course's information.

    This endpoint allows authorized users to modify course details. Access is
    restricted to admins and instructors who have been assigned to teach the
    specific course being updated.

    Args:
        course_id: Unique identifier of the course to update
        course: Course update data containing modified fields
        db: Database session dependency
        current_user: Current authenticated user with course access validation

    Returns:
        CourseRead: The updated course information

    Raises:
        HTTPException: 404 if course is not found

    Access Level: ADMIN | INSTRUCTOR (with course access)
    """
    db_course = update_course(db, course_id=course_id, course=course)
    if db_course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return db_course


@router.delete("/{course_id}", response_model=CourseRead)
async def delete_course_endpoint(
    course_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(course_access_from_path()),
):
    """
    Delete a course from the system.

    This endpoint allows authorized users to permanently remove a course from
    the system. Access is restricted to admins and instructors who have been
    assigned to teach the specific course being deleted.

    Args:
        course_id: Unique identifier of the course to delete
        db: Database session dependency
        current_user: Current authenticated user with course access validation

    Returns:
        CourseRead: The deleted course information

    Raises:
        HTTPException: 404 if course is not found

    Access Level: ADMIN | INSTRUCTOR (with course access)
    """
    db_course = delete_course(db, course_id=course_id)
    if db_course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return db_course

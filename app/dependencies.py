from typing import Generator, Optional, Dict, Any, List
from fastapi import Depends, HTTPException, status, Query, Path
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, SQLModel, create_engine, select
from jose import JWTError, jwt
import os
from pydantic import BaseModel

# Import these from authentication.py
from app.crud.admin import get_admin
from app.utils.authentication import SECRET_KEY, ALGORITHM

# Database configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(os.path.dirname(BASE_DIR), "smile_in.db")
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=True,  # Set to False in production
)

# JWT Configuration
ACCESS_TOKEN_EXPIRE_MINUTES = 1440
# OAuth2 setup - Configure this to use the unified token endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")



# Token payload model
class TokenData(BaseModel):
    username: Optional[str] = None
    user_type: Optional[str] = None


def create_db_and_tables():
    """Create database and tables if they don't exist"""
    SQLModel.metadata.create_all(engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency for getting the database session."""
    with Session(engine) as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


async def get_current_user_data(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Unified dependency to get the current authenticated user from JWT token.
    Returns a dict with user object and user type.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_type: str = payload.get("user_type", "student")

        if username is None:
            raise credentials_exception

        token_data = TokenData(username=username, user_type=user_type)

    except JWTError:
        raise credentials_exception

    # Get user based on type
    if token_data.user_type == "student":
        # Import here to avoid circular imports
        from app.crud.student import get_student_by_username

        user = get_student_by_username(db, username=token_data.username)
    elif token_data.user_type == "instructor":
        # Import here to avoid circular imports
        from app.crud.instructor import get_instructor_by_username

        user = get_instructor_by_username(db, username=token_data.username)
    elif token_data.user_type == "admin":
        # Import here to avoid circular imports
        from app.crud.admin import get_admin_by_username

        user = get_admin_by_username(db, username=token_data.username)
    else:
        raise credentials_exception

    if user is None:
        raise credentials_exception

    return {"user": user, "user_type": token_data.user_type}


async def get_current_user(current_user_data=Depends(get_current_user_data)):
    """Get current user regardless of type"""
    return current_user_data["user"]


async def get_current_admin(current_user_data=Depends(get_current_user_data)):
    """Get current user only if admin"""
    if current_user_data["user_type"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized as admin"
        )
    return current_user_data["user"]


async def get_current_student(current_user_data=Depends(get_current_user_data)):
    """Get current user only if student"""
    if current_user_data["user_type"] != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized as student"
        )
    return current_user_data["user"]


async def get_current_instructor(current_user_data=Depends(get_current_user_data)):
    """Get current user only if instructor"""
    if current_user_data["user_type"] != "instructor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized as instructor"
        )
    return current_user_data["user"]


async def get_current_admin_or_instructor(
    current_user_data=Depends(get_current_user_data),
):
    """Get current user only if admin or instructor"""
    if current_user_data["user_type"] not in ["admin", "instructor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized as admin or instructor",
        )
    return {
        "user": current_user_data["user"],
        "user_type": current_user_data["user_type"],
    }


async def get_instructor_courses(
    instructor_id: int, db: Session = Depends(get_db)
) -> List[int]:
    """
    Get all courses assigned to an instructor.

    Args:
        instructor_id: The ID of the instructor
        db: Database session

    Returns:
        List of course IDs the instructor has access to
    """
    # Import the InstructorCourse model here to avoid circular imports
    from app.models.instructor_course import InstructorCourse

    # Query to get all course IDs assigned to this instructor
    query = select(InstructorCourse.course_id).where(
        InstructorCourse.instructor_id == instructor_id
    )
    result = db.execute(query).fetchall()

    # Extract course IDs from the query result
    return [row[0] for row in result]


async def validate_instructor_course_access(
    course_id: int,
    instructor=Depends(get_current_instructor),
    db: Session = Depends(get_db),
):
    """
    Dependency to validate that an instructor has access to a specific course.

    Args:
        course_id: The ID of the course to validate access for
        instructor: The current instructor (from get_current_instructor)
        db: Database session

    Returns:
        The instructor object if validation passes

    Raises:
        HTTPException if the instructor does not have access to the course
    """
    # Get the courses this instructor has access to
    accessible_courses = await get_instructor_courses(instructor.instructor_id, db)

    # Check if the requested course is in the accessible courses
    if course_id not in accessible_courses:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You don't have access to course with ID {course_id}",
        )

    return instructor


async def validate_admin_instructor_course_access(
    course_id: int,
    user_data=Depends(get_current_admin_or_instructor),
    db: Session = Depends(get_db),
):
    """
    Dependency to validate access to a course for both admin and instructors.
    Admins have access to all courses, while instructors only have access to their assigned courses.

    Args:
        course_id: The ID of the course to validate access for
        user_data: Dictionary containing user and user_type
        db: Database session

    Returns:
        The user object if validation passes

    Raises:
        HTTPException if the user does not have access to the course
    """
    user = user_data["user"]
    user_type = user_data["user_type"]

    # Admins have access to all courses
    if user_type == "admin":
        return user

    # For instructors, check their course assignments
    if user_type == "instructor":
        accessible_courses = await get_instructor_courses(user.instructor_id, db)

        if course_id not in accessible_courses:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You don't have access to course with ID {course_id}",
            )

    return user


# Function to create a dependency that validates course access from path parameter
def course_access_from_path(course_id_param: str = "course_id"):
    """
    Creates a dependency that validates admin or instructor access to a course
    specified in the path parameter.

    Args:
        course_id_param: The name of the path parameter containing the course ID

    Returns:
        A dependency function that validates course access
    """

    async def validate_access(
        course_id: int = Path(..., alias=course_id_param),
        user_data=Depends(get_current_admin_or_instructor),
        db: Session = Depends(get_db),
    ):
        return await validate_admin_instructor_course_access(course_id, user_data, db)

    return validate_access


# Function to create a dependency that validates course access from query parameter
def course_access_from_query(course_id_param: str = "course_id"):
    """
    Creates a dependency that validates admin or instructor access to a course
    specified in the query parameter.

    Args:
        course_id_param: The name of the query parameter containing the course ID

    Returns:
        A dependency function that validates course access
    """

    async def validate_access(
        course_id: int = Query(..., alias=course_id_param),
        user_data=Depends(get_current_admin_or_instructor),
        db: Session = Depends(get_db),
    ):
        return await validate_admin_instructor_course_access(course_id, user_data, db)

    return validate_access


async def validate_instructor_self_access(
    instructor_id: int,
    current_instructor=Depends(get_current_instructor),
    db: Session = Depends(get_db),
):
    """
    Dependency to validate that an instructor has access to their own data.

    Args:
        instructor_id: The ID of the instructor to validate access for
        current_instructor: The current authenticated instructor
        db: Database session

    Returns:
        The instructor object if validation passes

    Raises:
        HTTPException if the instructor does not have access
    """
    # Check if the requested instructor_id matches the current instructor's ID
    if instructor_id != current_instructor.instructor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this instructor's data",
        )

    return current_instructor


async def validate_admin_instructor_self_access(
    instructor_id: int,
    user_data=Depends(get_current_admin_or_instructor),
    db: Session = Depends(get_db),
):
    """
    Dependency to validate access to instructor data for both admin and instructors.
    Admins have access to all instructor data, while instructors only have access to their own data.

    Args:
        instructor_id: The ID of the instructor to validate access for
        user_data: Dictionary containing user and user_type
        db: Database session

    Returns:
        The user object if validation passes

    Raises:
        HTTPException if the user does not have access
    """
    user = user_data["user"]
    user_type = user_data["user_type"]

    # Admins have access to all instructor data
    if user_type == "admin":
        return user

    # For instructors, check if they're accessing their own data
    if user_type == "instructor":
        if instructor_id != user.instructor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this instructor's data",
            )

    return user


# Function to create a dependency that validates instructor access from path parameter
def instructor_access_from_path(instructor_id_param: str = "instructor_id"):
    """
    Creates a dependency that validates admin or instructor access to instructor data
    specified in the path parameter.

    Args:
        instructor_id_param: The name of the path parameter containing the instructor ID

    Returns:
        A dependency function that validates instructor access
    """

    async def validate_access(
        instructor_id: int = Path(..., alias=instructor_id_param),
        user_data=Depends(get_current_admin_or_instructor),
        db: Session = Depends(get_db),
    ):
        return await validate_admin_instructor_self_access(instructor_id, user_data, db)

    return validate_access


# Function to create a dependency that validates instructor access from query parameter
def instructor_access_from_query(instructor_id_param: str = "instructor_id"):
    """
    Creates a dependency that validates admin or instructor access to instructor data
    specified in the query parameter.

    Args:
        instructor_id_param: The name of the query parameter containing the instructor ID

    Returns:
        A dependency function that validates instructor access
    """

    async def validate_access(
        instructor_id: int = Query(..., alias=instructor_id_param),
        user_data=Depends(get_current_admin_or_instructor),
        db: Session = Depends(get_db),
    ):
        return await validate_admin_instructor_self_access(instructor_id, user_data, db)

    return validate_access

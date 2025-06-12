from sqlmodel import Session, select

from app.models.instructor import Instructor
from app.schemas.instructor import InstructorCreate, InstructorUpdate
from app.utils.authentication import get_password_hash, verify_password
from app.utils.time_utils import get_indonesia_time


def create_instructor(db: Session, instructor: InstructorCreate) -> Instructor:
    """
    Create a new instructor account.

    Creates a new instructor with hashed password and timestamp information.
    Password is automatically hashed for security before storing in database.
    Sets both created_at and updated_at timestamps to current Indonesia time.

    Args:
        db: Database session for transaction management
        instructor: Validated instructor data from registration request

    Returns:
        Instructor: Newly created instructor with generated ID and hashed password

    Raises:
        SQLAlchemyError: If database operation fails
        IntegrityError: If username/email already exists
    """
    hashed_password = get_password_hash(instructor.password)

    db_instructor = Instructor(
        full_name=instructor.full_name,
        username=instructor.username,
        password=hashed_password,
        nidn=instructor.nidn,
        email=instructor.email,
        phone_number=instructor.phone_number,
        profile_picture_url=instructor.profile_picture_url,
        created_at=get_indonesia_time(),
        updated_at=get_indonesia_time(),
    )
    db.add(db_instructor)
    db.commit()
    db.refresh(db_instructor)
    return db_instructor


def get_next_instructor(db: Session, current_instructor_id: int) -> Instructor | None:
    """
    Get the next instructor in sequence by ID with circular navigation.

    Finds the instructor with the smallest ID greater than current instructor.
    If no instructor found with higher ID, returns the instructor with lowest ID
    to provide circular navigation functionality for UI components.

    Args:
        db: Database session for query execution
        current_instructor_id: ID of current instructor as reference point

    Returns:
        Instructor | None: Next instructor in sequence or None if no instructors exist
    """
    next_instructor = db.exec(
        select(Instructor)
        .where(Instructor.instructor_id > current_instructor_id)
        .order_by(Instructor.instructor_id)
        .limit(1)
    ).first()

    if next_instructor is None:
        next_instructor = db.exec(
            select(Instructor).order_by(Instructor.instructor_id).limit(1)
        ).first()

    return next_instructor


def get_instructors(db: Session, skip: int = 0, limit: int = 100) -> list[Instructor]:
    """
    Retrieve a paginated list of instructors.

    Fetches instructors with pagination support for efficient data loading.
    Results are ordered by default database ordering (typically by ID).

    Args:
        db: Database session for query execution
        skip: Number of records to skip for pagination (default: 0)
        limit: Maximum number of records to return (default: 100)

    Returns:
        list[Instructor]: List of instructor records
    """
    return db.exec(select(Instructor).offset(skip).limit(limit)).all()


def get_instructor(db: Session, instructor_id: int) -> Instructor | None:
    """
    Retrieve a specific instructor by ID.

    Fetches a single instructor using primary key lookup for optimal performance.
    Returns None if instructor not found instead of raising exception.

    Args:
        db: Database session for query execution
        instructor_id: Unique identifier of the instructor

    Returns:
        Instructor | None: The requested instructor or None if not found
    """
    return db.get(Instructor, instructor_id)


def get_instructor_by_username(db: Session, username: str) -> Instructor | None:
    """
    Retrieve an instructor by username.

    Finds instructor using unique username field, commonly used for
    authentication and user lookup operations.

    Args:
        db: Database session for query execution
        username: Unique username of the instructor

    Returns:
        Instructor | None: The instructor with matching username or None if not found
    """
    return db.exec(select(Instructor).where(Instructor.username == username)).first()


def update_instructor(
    db: Session, instructor_id: int, instructor: InstructorUpdate
) -> Instructor | None:
    """
    Update an existing instructor's information.

    Performs partial update of instructor data with automatic password hashing
    if password is included in update. Updates timestamp to current time and
    validates instructor existence before proceeding with update operation.

    Args:
        db: Database session for transaction management
        instructor_id: ID of instructor to update
        instructor: Partial instructor data for update

    Returns:
        Instructor | None: Updated instructor or None if not found

    Raises:
        SQLAlchemyError: If database operation fails
    """
    db_instructor = db.get(Instructor, instructor_id)
    if db_instructor is None:
        return None

    instructor_data = instructor.dict(exclude_unset=True)

    if "password" in instructor_data:
        instructor_data["password"] = get_password_hash(instructor_data["password"])

    instructor_data["updated_at"] = get_indonesia_time()

    for key, value in instructor_data.items():
        setattr(db_instructor, key, value)

    db.add(db_instructor)
    db.commit()
    db.refresh(db_instructor)
    return db_instructor


def delete_instructor(db: Session, instructor_id: int) -> bool:
    """
    Delete an instructor by ID.

    Removes instructor from database after validating existence.
    Returns boolean status to indicate success or failure of deletion operation.

    Args:
        db: Database session for transaction management
        instructor_id: ID of instructor to delete

    Returns:
        bool: True if deletion successful, False if instructor not found

    Raises:
        SQLAlchemyError: If database operation fails
    """
    instructor = db.get(Instructor, instructor_id)
    if instructor is None:
        return False

    db.delete(instructor)
    db.commit()
    return True


def change_instructor_password(
    db: Session, instructor_id: int, current_password: str, new_password: str
) -> Instructor | None | bool:
    """
    Change an instructor's password with current password verification.

    Securely updates instructor password by first verifying the current password
    before applying the new one. New password is automatically hashed and
    updated_at timestamp is refreshed for audit trail purposes.

    Args:
        db: Database session for transaction management
        instructor_id: ID of instructor changing password
        current_password: Current plain text password for verification
        new_password: New plain text password to be hashed and stored

    Returns:
        Instructor: Updated instructor if successful
        None: If instructor not found
        False: If current password verification fails

    Raises:
        SQLAlchemyError: If database operation fails
    """
    db_instructor = db.get(Instructor, instructor_id)
    if db_instructor is None:
        return None

    if not verify_password(current_password, db_instructor.password):
        return False

    db_instructor.password = get_password_hash(new_password)
    db_instructor.updated_at = get_indonesia_time()

    db.add(db_instructor)
    db.commit()
    db.refresh(db_instructor)
    return db_instructor

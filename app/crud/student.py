import json
from typing import Dict, Any, List, Optional

from sqlmodel import Session, delete, select

from app.models.schedule import Schedule
from app.models.student import Student
from app.schemas.student import StudentCreate, StudentUpdate
from app.utils.authentication import get_password_hash
from app.utils.time_utils import get_indonesia_time


def create_student(db: Session, student: StudentCreate) -> Student:
    """
    Create a new student account with secure password hashing and face data serialization.

    This function handles the complete student registration process including password
    security through hashing, face recognition data serialization for biometric features,
    and database persistence. The face data is stored as JSON string for compatibility
    with various database systems while maintaining data structure integrity.

    Args:
        db (Session): Active database session for executing queries
        student (StudentCreate): Student registration data containing username, password,
                               personal information, and optional face recognition data

    Returns:
        Student: Newly created student object with generated ID and hashed password
    """
    hashed_password = get_password_hash(student.password)

    student_data = student.model_dump()
    student_data["password"] = hashed_password

    if student_data.get("face_data"):
        student_data["face_data"] = json.dumps(student_data["face_data"])

    db_student = Student(**student_data)
    db.add(db_student)
    db.commit()
    db.refresh(db_student)

    return db_student


def get_students(db: Session, skip: int = 0, limit: int = 100) -> List[Student]:
    """
    Retrieve a paginated list of students with deserialized face recognition data.

    This function fetches student records with pagination support and automatically
    deserializes face recognition data from JSON strings back to Python objects.
    It includes error handling for corrupted face data to ensure system stability
    when biometric data becomes invalid or corrupted.

    Args:
        db (Session): Active database session for executing queries
        skip (int): Number of records to skip for pagination (default: 0)
        limit (int): Maximum number of records to return (default: 100)

    Returns:
        List[Student]: List of student objects with deserialized face data
    """
    students = db.exec(select(Student).offset(skip).limit(limit)).all()

    for student in students:
        if student.face_data:
            try:
                student.face_data = json.loads(student.face_data)
            except json.JSONDecodeError:
                student.face_data = None

    return students


def get_student(db: Session, student_id: int) -> Optional[Student]:
    """
    Retrieve a specific student by ID with face data deserialization.

    This function fetches a single student record and handles the deserialization
    of face recognition data from JSON format. It provides safe handling of
    corrupted biometric data to prevent system failures during authentication
    or profile access operations.

    Args:
        db (Session): Active database session for executing queries
        student_id (int): Unique identifier of the student to retrieve

    Returns:
        Optional[Student]: Student object if found, None otherwise
    """
    student = db.get(Student, student_id)

    if student and student.face_data:
        try:
            student.face_data = json.loads(student.face_data)
        except json.JSONDecodeError:
            student.face_data = None

    return student


def get_student_by_username(db: Session, username: str) -> Optional[Student]:
    """
    Retrieve a student by their unique username for authentication purposes.

    This function is primarily used during login and authentication processes
    where the username serves as the primary identifier. It includes face data
    deserialization to support biometric authentication features alongside
    traditional username/password authentication methods.

    Args:
        db (Session): Active database session for executing queries
        username (str): Unique username of the student account

    Returns:
        Optional[Student]: Student object if username exists, None otherwise
    """
    student = db.exec(select(Student).where(Student.username == username)).first()

    if student and student.face_data:
        try:
            student.face_data = json.loads(student.face_data)
        except json.JSONDecodeError:
            student.face_data = None

    return student


def get_student_by_nim(db: Session, nim: str) -> Optional[Student]:
    """
    Retrieve a student by their unique student identification number (NIM).

    This function provides an alternative lookup method using the institutional
    student ID number, which is commonly used in academic systems for student
    identification. It supports various student management operations where
    NIM is the preferred identifier over username.

    Args:
        db (Session): Active database session for executing queries
        nim (str): Unique student identification number

    Returns:
        Optional[Student]: Student object if NIM exists, None otherwise
    """
    student = db.exec(select(Student).where(Student.nim == nim)).first()

    if student and student.face_data:
        try:
            student.face_data = json.loads(student.face_data)
        except json.JSONDecodeError:
            student.face_data = None

    return student


def get_next_student(db: Session, current_student_id: int) -> Optional[Student]:
    """
    Navigate to the next student in sequence with circular iteration support.

    This function implements a navigation system for cycling through student records
    in ascending ID order. When reaching the highest ID, it automatically wraps
    around to the lowest ID, providing seamless circular navigation for
    administrative interfaces or sequential processing operations.

    Args:
        db (Session): Active database session for executing queries
        current_student_id (int): ID of the current student as reference point

    Returns:
        Optional[Student]: Next student in sequence, or first student if at end
    """
    next_student = db.exec(
        select(Student)
        .where(Student.student_id > current_student_id)
        .order_by(Student.student_id)
        .limit(1)
    ).first()

    if next_student is None:
        next_student = db.exec(
            select(Student).order_by(Student.student_id).limit(1)
        ).first()

    return next_student


def update_student(
    db: Session, student_id: int, student: StudentUpdate
) -> Optional[Student]:
    """
    Update student information with selective field modification and security handling.

    This function supports partial updates of student records while maintaining
    data security through password re-hashing when changed and proper serialization
    of face recognition data. It automatically updates the modification timestamp
    and preserves existing data for fields not included in the update request.

    Args:
        db (Session): Active database session for executing queries
        student_id (int): Unique identifier of the student to update
        student (StudentUpdate): Partial student data with fields to modify

    Returns:
        Optional[Student]: Updated student object with deserialized face data,
                          None if student not found
    """
    db_student = db.get(Student, student_id)
    if db_student is None:
        return None

    student_data = student.model_dump(exclude_unset=True)

    if "password" in student_data and student_data["password"]:
        student_data["password"] = get_password_hash(student_data["password"])

    if "face_data" in student_data and student_data["face_data"]:
        student_data["face_data"] = json.dumps(student_data["face_data"])

    student_data["updated_at"] = get_indonesia_time()

    for key, value in student_data.items():
        setattr(db_student, key, value)

    db.add(db_student)
    db.commit()
    db.refresh(db_student)

    if db_student.face_data:
        try:
            db_student.face_data = json.loads(db_student.face_data)
        except json.JSONDecodeError:
            db_student.face_data = None

    return db_student


def delete_student(db: Session, student_id: int) -> bool:
    """
    Delete a student account with cascading cleanup of related schedule records.

    This function performs a complete student account deletion including cleanup
    of associated schedule records to maintain referential integrity. It implements
    robust error handling for different database schema configurations and ensures
    transactional consistency during the deletion process.

    Args:
        db (Session): Active database session for executing queries
        student_id (int): Unique identifier of the student to delete

    Returns:
        bool: True if deletion successful, False if student not found
    """
    student = db.exec(select(Student).where(Student.student_id == student_id)).first()
    if not student:
        return False

    try:
        db.exec(delete(Schedule).where(Schedule.student_id == student_id))
    except AttributeError:
        try:
            db.exec(delete(Schedule).where(Schedule.student == student_id))
        except AttributeError:
            pass

    db.delete(student)
    db.commit()

    return True


def update_face_data(
    db: Session, student_id: int, face_data: Dict[str, Any]
) -> Optional[Student]:
    """
    Update biometric face recognition data for enhanced security authentication.

    This function specifically handles updates to face recognition data used for
    biometric authentication systems. It serializes the complex face data structure
    to JSON format for database storage while maintaining data integrity and
    automatically updating the modification timestamp for audit purposes.

    Args:
        db (Session): Active database session for executing queries
        student_id (int): Unique identifier of the student
        face_data (Dict[str, Any]): Face recognition data structure containing
                                   biometric features and authentication parameters

    Returns:
        Optional[Student]: Updated student object with new face data,
                          None if student not found
    """
    db_student = db.get(Student, student_id)
    if db_student is None:
        return None

    db_student.face_data = json.dumps(face_data)
    db_student.updated_at = get_indonesia_time()

    db.add(db_student)
    db.commit()
    db.refresh(db_student)

    try:
        db_student.face_data = json.loads(db_student.face_data)
    except json.JSONDecodeError:
        db_student.face_data = None

    return db_student

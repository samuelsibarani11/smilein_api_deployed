from sqlmodel import Session, select
from fastapi import HTTPException, status

from app.models.course import Course
from app.schemas.course import CourseCreate, CourseUpdate
from app.utils.time_utils import get_indonesia_time


def get_courses(db: Session, skip: int = 0, limit: int = 100) -> list[Course]:
    """
    Mengambil daftar course dengan pagination.

    Menjalankan query untuk mendapatkan semua course dengan offset dan limit
    untuk mendukung pagination, mengembalikan list course yang tersedia.
    """
    return db.exec(select(Course).offset(skip).limit(limit)).all()


def get_course_by_id(db: Session, course_id: int) -> Course:
    """
    Mengambil course berdasarkan ID dengan error handling.

    Mencari course berdasarkan ID yang diberikan, melemparkan HTTPException
    dengan status 404 jika course tidak ditemukan dalam database.
    """
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with ID {course_id} not found",
        )
    return course


def create_course(db: Session, course: CourseCreate) -> Course:
    """
    Membuat course baru dalam database.

    Membuat instance Course dengan data dari schema, mengatur timestamp
    created_at secara otomatis, dan menyimpannya ke database.
    """
    db_course = Course(
        course_name=course.course_name, sks=course.sks, created_at=get_indonesia_time()
    )
    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    return db_course


def update_course(db: Session, course_id: int, course: CourseUpdate) -> Course:
    """
    Memperbarui course yang sudah ada.

    Mengambil course berdasarkan ID, memperbarui field yang diberikan
    dalam request, dan menyimpan perubahan ke database.
    """
    db_course = get_course_by_id(db, course_id)

    course_data = course.dict(exclude_unset=True)
    for key, value in course_data.items():
        setattr(db_course, key, value)

    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    return db_course


def delete_course(db: Session, course_id: int) -> Course:
    """
    Menghapus course dengan validasi referential integrity.

    Mengecek apakah course memiliki schedule terkait sebelum menghapus,
    melemparkan HTTPException jika course masih digunakan, atau menghapus jika aman.
    """
    db_course = get_course_by_id(db, course_id)

    if db_course.schedules and len(db_course.schedules) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Course with ID {course_id} cannot be deleted because it is currently in use (has associated schedules)",
        )

    db.delete(db_course)
    db.commit()
    return db_course

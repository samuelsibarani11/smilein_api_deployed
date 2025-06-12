from datetime import datetime, time
import json

from sqlmodel import Session, select
from sqlalchemy.orm import selectinload

from app.models.attendance import Attendance
from app.models.schedule import Schedule
from app.schemas.attendance import (
    AttendanceCreate,
    AttendanceUpdate,
    AttendanceCheckIn,
    MultipleAttendanceCreate,
)
from app.utils.time_utils import get_indonesia_date, get_indonesia_time


def create_attendance(db: Session, attendance: AttendanceCreate) -> Attendance:
    """
    Membuat record kehadiran baru untuk siswa pada jadwal tertentu.

    Membuat attendance record dengan status default ABSENT dan tanggal hari ini,
    tanpa data check-in. Record ini akan diupdate ketika siswa melakukan check-in.
    """
    today = get_indonesia_date()

    db_attendance = Attendance(
        student_id=attendance.student_id,
        schedule_id=attendance.schedule_id,
        date=today,
        check_in_time=None,
        status="ABSENT",
        location_data=None,
        face_verification_data=None,
        smile_detected=False,
        image_captured=None,
        now=get_indonesia_time(),
    )
    db.add(db_attendance)
    db.commit()
    db.refresh(db_attendance)
    return db_attendance


def create_multiple_attendances(
    db: Session, multiple_attendance: MultipleAttendanceCreate
) -> list[Attendance]:
    """
    Membuat record kehadiran untuk beberapa siswa sekaligus pada jadwal yang sama.

    Melakukan bulk create attendance records dengan status default ABSENT,
    efisien untuk inisialisasi kehadiran kelas pada awal hari.
    """
    created_attendances = []
    today = get_indonesia_date()

    for student_id in multiple_attendance.student_ids:
        db_attendance = Attendance(
            student_id=student_id,
            schedule_id=multiple_attendance.schedule_id,
            date=today,
            check_in_time=None,
            status="ABSENT",
            location_data=None,
            face_verification_data=None,
            smile_detected=False,
            image_captured=None,
            now=get_indonesia_time(),
        )
        db.add(db_attendance)
        created_attendances.append(db_attendance)

    db.commit()

    for attendance in created_attendances:
        db.refresh(attendance)

    return created_attendances


def student_check_in(
    db: Session,
    attendance_id: int,
    check_in_data: AttendanceCheckIn,
    image_captured_url: str = None,
) -> Attendance | None:
    """
    Memproses check-in siswa pada record kehadiran yang sudah ada.

    Mengupdate attendance record dengan waktu check-in, data lokasi, verifikasi wajah,
    deteksi senyum, dan gambar. Menentukan status PRESENT atau LATE berdasarkan jadwal.
    """
    attendance = db.get(Attendance, attendance_id)
    if attendance is None:
        return None

    now = get_indonesia_time()
    attendance.check_in_time = check_in_data.check_in_time or now

    schedule = db.get(Schedule, attendance.schedule_id)
    if schedule:
        today = get_indonesia_date()
        start_time_parts = schedule.start_time.split(":")
        schedule_start = time(
            hour=int(start_time_parts[0]),
            minute=int(start_time_parts[1]),
            second=int(start_time_parts[2]) if len(start_time_parts) > 2 else 0,
        )
        start_time = datetime.combine(today, schedule_start)

        check_in_time = attendance.check_in_time
        if check_in_time.tzinfo is not None:
            check_in_time = check_in_time.replace(tzinfo=None)

        if check_in_time > start_time:
            attendance.status = "LATE"
        else:
            attendance.status = "PRESENT"
    else:
        attendance.status = "PRESENT"

    if check_in_data.location_data:
        attendance.location_data = process_json_field(check_in_data.location_data)

    if check_in_data.face_verification_data:
        attendance.face_verification_data = process_json_field(
            check_in_data.face_verification_data
        )

    if check_in_data.smile_detected is not None:
        attendance.smile_detected = check_in_data.smile_detected

    if image_captured_url is not None:
        attendance.image_captured_url = image_captured_url

    db.add(attendance)
    db.commit()
    db.refresh(attendance)
    return attendance


def get_active_student_schedule(db: Session, student_id: int) -> list[Schedule]:
    """
    Mendapatkan jadwal aktif siswa berdasarkan hari dan waktu saat ini.

    Mencari jadwal yang sedang berlangsung untuk siswa tertentu,
    memeriksa apakah siswa sudah memiliki record kehadiran untuk jadwal tersebut.
    """
    current_day = datetime.today().weekday() + 1
    current_time = datetime.now().strftime("%H:%M:%S")

    active_schedules = (
        db.query(Schedule)
        .filter(
            Schedule.day_of_week == current_day,
            Schedule.start_time <= current_time,
            Schedule.end_time >= current_time,
        )
        .all()
    )

    schedule_ids = [schedule.schedule_id for schedule in active_schedules]

    if schedule_ids:
        today = datetime.today().date()
        existing_attendances = (
            db.query(Attendance)
            .filter(
                Attendance.student_id == student_id,
                Attendance.schedule_id.in_(schedule_ids),
                Attendance.date == today,
            )
            .all()
        )

        if existing_attendances:
            return active_schedules

    return active_schedules


def process_json_field(data) -> dict | None:
    """
    Memproses dan memvalidasi data JSON untuk field attendance.

    Mengkonversi berbagai tipe data menjadi format dict yang konsisten,
    menangani string JSON, primitif types, dan error handling untuk data corrupt.
    """
    if data is None:
        return None

    if isinstance(data, dict):
        return data

    if isinstance(data, (str, int, float)):
        if isinstance(data, (int, float)):
            return {"data": str(data)}
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return {"data": str(data)}

    return {"data": str(data)}


def get_attendances(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    student_id: int = None,
    schedule_id: int = None,
    course_id: int = None,
) -> list[dict]:
    """
    Mengambil daftar kehadiran dengan relasi lengkap dalam format nested objects.

    Melakukan eager loading untuk semua relasi (student, schedule, course, room, instructor),
    menerapkan filter berdasarkan parameter, dan mengembalikan data terstruktur dengan pagination.
    """
    query = db.query(Attendance).options(
        selectinload(Attendance.student),
        selectinload(Attendance.schedule),
        selectinload(Attendance.schedule).selectinload(Schedule.course),
        selectinload(Attendance.schedule).selectinload(Schedule.room),
        selectinload(Attendance.schedule).selectinload(Schedule.instructor),
    )

    if student_id:
        query = query.filter(Attendance.student_id == student_id)
    if schedule_id:
        query = query.filter(Attendance.schedule_id == schedule_id)
    if course_id:
        query = query.filter(Schedule.course_id == course_id)

    attendances = query.offset(skip).limit(limit).all()

    result = []
    for attendance in attendances:
        attendance_data = {
            "attendance_id": attendance.attendance_id,
            "date": attendance.date,
            "check_in_time": attendance.check_in_time,
            "status": attendance.status,
            "location_data": process_json_field(attendance.location_data),
            "face_verification_data": process_json_field(
                attendance.face_verification_data
            ),
            "smile_detected": attendance.smile_detected,
            "image_captured_url": attendance.image_captured_url,
            "created_at": attendance.created_at,
            "updated_at": attendance.updated_at,
            "student": {"id": attendance.student_id},
            "schedule": {"id": attendance.schedule_id},
        }

        if attendance.student:
            student_obj = attendance_data["student"]
            for attr_name in dir(attendance.student):
                if not attr_name.startswith("_") and attr_name not in [
                    "metadata",
                    "registry",
                    "attendances",
                ]:
                    try:
                        value = getattr(attendance.student, attr_name)
                        if callable(value):
                            continue
                        student_obj[attr_name] = value
                    except:  # noqa: E722
                        pass

        if attendance.schedule:
            schedule_obj = attendance_data["schedule"]
            for attr_name in dir(attendance.schedule):
                if not attr_name.startswith("_") and attr_name not in [
                    "metadata",
                    "registry",
                    "course",
                    "room",
                    "instructor",
                    "attendances",
                ]:
                    try:
                        value = getattr(attendance.schedule, attr_name)
                        if callable(value):
                            continue
                        schedule_obj[attr_name] = value
                    except:  # noqa: E722
                        pass

            if hasattr(attendance.schedule, "course") and attendance.schedule.course:
                course_obj = {}
                for attr_name in dir(attendance.schedule.course):
                    if not attr_name.startswith("_") and attr_name not in [
                        "metadata",
                        "registry",
                        "schedules",
                    ]:
                        try:
                            value = getattr(attendance.schedule.course, attr_name)
                            if callable(value):
                                continue
                            course_obj[attr_name] = value
                        except:  # noqa: E722
                            pass
                schedule_obj["course"] = course_obj

            if attendance.schedule.room:
                room_obj = {}
                for attr_name in dir(attendance.schedule.room):
                    if not attr_name.startswith("_") and attr_name not in [
                        "metadata",
                        "registry",
                        "schedules",
                    ]:
                        try:
                            value = getattr(attendance.schedule.room, attr_name)
                            if callable(value):
                                continue
                            room_obj[attr_name] = value
                        except:  # noqa: E722
                            pass
                schedule_obj["room"] = room_obj

            if (
                hasattr(attendance.schedule, "instructor")
                and attendance.schedule.instructor
            ):
                instructor_obj = {}
                for attr_name in dir(attendance.schedule.instructor):
                    if not attr_name.startswith("_") and attr_name not in [
                        "metadata",
                        "registry",
                        "schedules",
                    ]:
                        try:
                            value = getattr(attendance.schedule.instructor, attr_name)
                            if callable(value):
                                continue
                            instructor_obj[attr_name] = value
                        except:  # noqa: E722
                            pass
                schedule_obj["instructor"] = instructor_obj

        result.append(attendance_data)

    return result


def get_day_name(day_number: int) -> str:
    """
    Mengkonversi nomor hari menjadi nama hari dalam bahasa Indonesia.

    Helper function untuk menampilkan nama hari yang user-friendly
    dari format angka 1-7 yang digunakan dalam database.
    """
    days = {
        1: "Senin",
        2: "Selasa",
        3: "Rabu",
        4: "Kamis",
        5: "Jumat",
        6: "Sabtu",
        7: "Minggu",
    }
    return days.get(day_number, "Unknown")


def get_attendance(db: Session, attendance_id: int) -> Attendance | None:
    """
    Mengambil single attendance record berdasarkan ID dengan relasi lengkap.

    Melakukan eager loading untuk student dan schedule relationships,
    memproses JSON fields, dan mengembalikan attendance object yang lengkap.
    """
    attendance = db.exec(
        select(Attendance)
        .where(Attendance.attendance_id == attendance_id)
        .options(
            selectinload(Attendance.student),
            selectinload(Attendance.schedule),
        )
    ).first()

    if attendance:
        attendance.location_data = process_json_field(attendance.location_data)
        attendance.face_verification_data = process_json_field(
            attendance.face_verification_data
        )

    return attendance


def get_student_attendances(
    db: Session,
    student_id: int,
    schedule_id: int = None,
    skip: int = 0,
    limit: int = 100,
) -> list[dict]:
    """
    Mengambil semua record kehadiran untuk siswa tertentu dengan nested objects.

    Melakukan query dengan eager loading untuk semua relasi, menerapkan filter schedule
    jika diperlukan, dan mengembalikan data terstruktur dengan pagination.
    """
    query = (
        db.query(Attendance)
        .options(
            selectinload(Attendance.student),
            selectinload(Attendance.schedule),
            selectinload(Attendance.schedule).selectinload(Schedule.course),
            selectinload(Attendance.schedule).selectinload(Schedule.room),
            selectinload(Attendance.schedule).selectinload(Schedule.instructor),
        )
        .filter(Attendance.student_id == student_id)
    )

    if schedule_id:
        query = query.filter(Attendance.schedule_id == schedule_id)

    attendances = query.offset(skip).limit(limit).all()

    result = []
    for attendance in attendances:
        attendance_data = {
            "attendance_id": attendance.attendance_id,
            "date": attendance.date,
            "check_in_time": attendance.check_in_time,
            "status": attendance.status,
            "location_data": process_json_field(attendance.location_data),
            "face_verification_data": process_json_field(
                attendance.face_verification_data
            ),
            "smile_detected": attendance.smile_detected,
            "image_captured_url": attendance.image_captured_url,
            "created_at": attendance.created_at,
            "updated_at": attendance.updated_at,
            "student": {"id": attendance.student_id},
            "schedule": {"id": attendance.schedule_id},
        }

        if attendance.student:
            student_obj = attendance_data["student"]
            for attr_name in dir(attendance.student):
                if not attr_name.startswith("_") and attr_name not in [
                    "metadata",
                    "registry",
                    "attendances",
                ]:
                    try:
                        value = getattr(attendance.student, attr_name)
                        if callable(value):
                            continue
                        student_obj[attr_name] = value
                    except:  # noqa: E722
                        pass

        if attendance.schedule:
            schedule_obj = attendance_data["schedule"]
            for attr_name in dir(attendance.schedule):
                if not attr_name.startswith("_") and attr_name not in [
                    "metadata",
                    "registry",
                    "course",
                    "room",
                    "instructor",
                    "attendances",
                ]:
                    try:
                        value = getattr(attendance.schedule, attr_name)
                        if callable(value):
                            continue
                        schedule_obj[attr_name] = value
                    except:  # noqa: E722
                        pass

            if hasattr(attendance.schedule, "course") and attendance.schedule.course:
                course_obj = {}
                for attr_name in dir(attendance.schedule.course):
                    if not attr_name.startswith("_") and attr_name not in [
                        "metadata",
                        "registry",
                        "schedules",
                    ]:
                        try:
                            value = getattr(attendance.schedule.course, attr_name)
                            if callable(value):
                                continue
                            course_obj[attr_name] = value
                        except:  # noqa: E722
                            pass
                schedule_obj["course"] = course_obj

            if attendance.schedule.room:
                room_obj = {}
                for attr_name in dir(attendance.schedule.room):
                    if not attr_name.startswith("_") and attr_name not in [
                        "metadata",
                        "registry",
                        "schedules",
                    ]:
                        try:
                            value = getattr(attendance.schedule.room, attr_name)
                            if callable(value):
                                continue
                            room_obj[attr_name] = value
                        except:  # noqa: E722
                            pass
                schedule_obj["room"] = room_obj

            if (
                hasattr(attendance.schedule, "instructor")
                and attendance.schedule.instructor
            ):
                instructor_obj = {}
                for attr_name in dir(attendance.schedule.instructor):
                    if not attr_name.startswith("_") and attr_name not in [
                        "metadata",
                        "registry",
                        "schedules",
                    ]:
                        try:
                            value = getattr(attendance.schedule.instructor, attr_name)
                            if callable(value):
                                continue
                            instructor_obj[attr_name] = value
                        except:  # noqa: E722
                            pass
                schedule_obj["instructor"] = instructor_obj

        result.append(attendance_data)

    return result


def get_course_attendances(
    db: Session, course_id: int, student_id: int = None
) -> list[Attendance]:
    """
    Mengambil semua record kehadiran untuk course tertentu.

    Mencari semua schedule yang terkait dengan course, kemudian mengambil
    semua attendance records untuk schedule tersebut dengan filter student optional.
    """
    schedule_query = select(Schedule).where(Schedule.course_id == course_id)
    schedules = db.exec(schedule_query).all()
    schedule_ids = [schedule.schedule_id for schedule in schedules]

    if not schedule_ids:
        return []

    query = (
        select(Attendance)
        .where(Attendance.schedule_id.in_(schedule_ids))
        .options(
            selectinload(Attendance.student),
            selectinload(Attendance.schedule),
        )
    )

    if student_id:
        query = query.where(Attendance.student_id == student_id)

    attendances = db.exec(query).all()

    for attendance in attendances:
        attendance.location_data = process_json_field(attendance.location_data)
        attendance.face_verification_data = process_json_field(
            attendance.face_verification_data
        )

    return attendances


def update_attendance(
    db: Session, attendance_id: int, attendance: AttendanceUpdate
) -> Attendance | None:
    """
    Memperbarui record kehadiran yang sudah ada.

    Mengambil attendance berdasarkan ID, memperbarui field yang diberikan,
    memproses JSON fields, dan menyimpan perubahan ke database.
    """
    db_attendance = db.get(Attendance, attendance_id)
    if db_attendance is None:
        return None

    attendance_data = attendance.dict(exclude_unset=True)
    for key, value in attendance_data.items():
        setattr(db_attendance, key, value)

    db.add(db_attendance)
    db.commit()
    db.refresh(db_attendance)

    db_attendance.location_data = process_json_field(db_attendance.location_data)
    db_attendance.face_verification_data = process_json_field(
        db_attendance.face_verification_data
    )

    return db_attendance


def delete_attendance(db: Session, attendance_id: int) -> bool:
    """
    Menghapus single record kehadiran dari database.

    Mencari attendance berdasarkan ID, menghapusnya jika ditemukan,
    dan mengembalikan status keberhasilan operasi.
    """
    attendance = db.get(Attendance, attendance_id)
    if attendance is None:
        return False

    db.delete(attendance)
    db.commit()
    return True


def delete_multiple_attendances(db: Session, attendance_ids: list[int]) -> int:
    """
    Menghapus beberapa record kehadiran sekaligus.

    Melakukan bulk delete untuk daftar attendance IDs yang diberikan,
    mengembalikan jumlah record yang berhasil dihapus.
    """
    deleted_count = 0
    for attendance_id in attendance_ids:
        attendance = db.get(Attendance, attendance_id)
        if attendance:
            db.delete(attendance)
            deleted_count += 1

    db.commit()
    return deleted_count


def find_student_attendance(
    db: Session, student_id: int, schedule_id: int
) -> Attendance | None:
    """
    Mencari record kehadiran siswa untuk jadwal tertentu pada hari ini.

    Helper function untuk mengecek apakah siswa sudah memiliki attendance record
    sebelum membuat yang baru atau melakukan update.
    """
    today = datetime.today().date()
    attendance = db.exec(
        select(Attendance).where(
            Attendance.student_id == student_id,
            Attendance.schedule_id == schedule_id,
            Attendance.date == today,
        )
    ).first()
    return attendance


def student_direct_check_in(
    db: Session,
    student_id: int,
    schedule_id: int,
    location_data=None,
    face_verification_data=None,
    smile_detected=False,
    image_captured_url=None,
) -> Attendance | None:
    """
    Melakukan direct check-in siswa dengan create atau update attendance record.

    Mengecek existing attendance record, jika ada maka update, jika tidak ada maka create.
    Menentukan status PRESENT atau LATE berdasarkan waktu jadwal, memproses semua data check-in.
    """
    today = datetime.today().date()
    existing_attendance = find_student_attendance(db, student_id, schedule_id)

    location_data = process_json_field(location_data)
    face_verification_data = process_json_field(face_verification_data)

    schedule = db.get(Schedule, schedule_id)
    if not schedule:
        return None

    now = datetime.now()

    start_time_parts = schedule.start_time.split(":")
    schedule_start = time(
        hour=int(start_time_parts[0]),
        minute=int(start_time_parts[1]),
        second=int(start_time_parts[2]) if len(start_time_parts) > 2 else 0,
    )
    start_time = datetime.combine(today, schedule_start)

    status = "PRESENT"
    if now > start_time:
        status = "LATE"

    if existing_attendance:
        existing_attendance.check_in_time = now
        existing_attendance.status = status
        existing_attendance.location_data = location_data
        existing_attendance.face_verification_data = face_verification_data
        existing_attendance.smile_detected = smile_detected
        existing_attendance.image_captured_url = image_captured_url
        db.add(existing_attendance)
        db.commit()
        db.refresh(existing_attendance)
        return existing_attendance
    else:
        new_attendance = Attendance(
            student_id=student_id,
            schedule_id=schedule_id,
            date=today,
            check_in_time=now,
            status=status,
            location_data=location_data,
            face_verification_data=face_verification_data,
            smile_detected=smile_detected,
            image_captured_url=image_captured_url,
            created_at=now,
        )
        db.add(new_attendance)
        db.commit()
        db.refresh(new_attendance)
        return new_attendance

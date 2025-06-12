import os
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from pydantic import parse_obj_as
from sqlmodel import Session

from app.dependencies import (
    get_current_admin_or_instructor,
    get_current_user,
    get_db,
)
from app.schemas.attendance import (
    AttendanceCreate,
    AttendanceRead,
    AttendanceUpdate,
    AttendanceWithNestedData,
    AttendanceCheckIn,
    MultipleAttendanceCreate,
    MultipleAttendanceDelete,
)
from app.crud.attendance import (
    create_attendance,
    create_multiple_attendances,
    student_check_in,
    get_active_student_schedule,
    get_attendances,
    get_attendance,
    get_student_attendances,
    update_attendance,
    delete_attendance,
    delete_multiple_attendances,
    process_json_field,
)
from app.crud.instructor_course import get_instructor_courses
from app.crud.schedule import get_schedule
from app.utils.time_utils import get_indonesia_time
from app.services.face_verification_service import student_check_in_with_verification

# Fix: Use absolute path or relative path from the app directory
# Get the directory where this file is located
current_dir = os.path.dirname(os.path.abspath(__file__))
# Go up one level to app directory, then to services
MODEL_PATH = os.path.join(
    current_dir,
    "..",
    "services",
    "model_face_recognition",
    "mobilenetv2_model-1a.keras",
)
# Normalize the path
MODEL_PATH = os.path.normpath(MODEL_PATH)

router = APIRouter(
    prefix="/attendances",
    tags=["attendances"],
)


@router.post("/", response_model=AttendanceRead)
def create_attendance_endpoint(
    attendance: AttendanceCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin_or_instructor),
):
    """
    Create a new attendance record for a student.
    Only admin and instructor users can create attendance records.
    Instructors can only create attendance for courses they are teaching.
    Initially creates record with ABSENT status until student checks in.
    """
    user_type = current_user["user_type"]

    if user_type not in ["admin", "instructor"]:
        raise HTTPException(
            status_code=403,
            detail="Only admins or instructors can create attendance records",
        )

    if user_type == "instructor":
        schedule = get_schedule(db, attendance.schedule_id)
        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")

        if not get_instructor_courses(
            db, current_user.instructor_id, schedule.course_id
        ):
            raise HTTPException(
                status_code=403,
                detail="You can only create attendance for courses you are teaching",
            )

    db_attendance = create_attendance(db=db, attendance=attendance)
    return db_attendance


@router.post("/multiple", response_model=List[AttendanceRead])
def create_multiple_attendances_endpoint(
    multiple_attendance: MultipleAttendanceCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin_or_instructor),
):
    """
    Create attendance records for multiple students simultaneously.
    Only admin and instructor users can create bulk attendance records.
    Validates instructor access to course and ensures at least one student ID is provided.
    """
    user_type = current_user["user_type"]
    if user_type not in ["admin", "instructor"]:
        raise HTTPException(
            status_code=403,
            detail="Only admins or instructors can create attendance records",
        )

    if not multiple_attendance.student_ids:
        raise HTTPException(
            status_code=400,
            detail="At least one student ID must be provided",
        )

    if user_type == "instructor":
        schedule = get_schedule(db, multiple_attendance.schedule_id)
        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")

        if not get_instructor_courses(
            db, current_user.instructor_id, schedule.course_id
        ):
            raise HTTPException(
                status_code=403,
                detail="You can only create attendance for courses you are teaching",
            )

    db_attendances = create_multiple_attendances(
        db=db, multiple_attendance=multiple_attendance
    )

    if not db_attendances:
        raise HTTPException(
            status_code=500,
            detail="Failed to create attendance records",
        )

    return db_attendances


@router.post("/{attendance_id}/check-in", response_model=AttendanceRead)
async def student_check_in_endpoint(
    attendance_id: int,
    location_data: str = Form(None),
    face_verification_data: str = Form(None),
    smile_detected: bool = Form(False),
    image_captured_url: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Process student check-in with face verification and location data.
    Students can only check in to their own attendance records with face verification.
    Admin and instructors can check in without verification for any student.
    Requires image upload for face verification process.
    """
    user_type = getattr(current_user, "role", None)

    attendance = get_attendance(db, attendance_id=attendance_id)
    if attendance is None:
        raise HTTPException(status_code=404, detail="Attendance record not found")

    if hasattr(current_user, "student_id"):
        if current_user.student_id != attendance.student_id:
            raise HTTPException(
                status_code=403,
                detail="You can only check in to your own attendance records",
            )
    elif user_type not in ["ADMIN", "INSTRUCTOR"]:
        raise HTTPException(
            status_code=403, detail="Unauthorized to check in for this attendance"
        )

    if hasattr(current_user, "instructor_id"):
        schedule = attendance.schedule
        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")

        if not get_instructor_courses(
            db, current_user.instructor_id, schedule.course_id
        ):
            raise HTTPException(
                status_code=403,
                detail="You can only manage attendance for courses you are teaching",
            )

    location_data_str = str(location_data) if location_data is not None else None
    face_verification_data_str = (
        str(face_verification_data) if face_verification_data is not None else None
    )

    check_in_data = AttendanceCheckIn(
        location_data=location_data_str,
        face_verification_data=face_verification_data_str,
        smile_detected=smile_detected,
    )

    if image_captured_url and image_captured_url.filename:
        valid_content_types = ["image/jpeg", "image/png", "image/jpg"]
        if image_captured_url.content_type not in valid_content_types:
            raise HTTPException(
                status_code=400,
                detail="File must be an image (JPEG, PNG, or JPG)",
            )
    else:
        raise HTTPException(
            status_code=400,
            detail="An image is required for face verification",
        )

    # Verify model file exists before proceeding
    if not os.path.exists(MODEL_PATH):
        raise HTTPException(
            status_code=500,
            detail=f"Face recognition model not found at {MODEL_PATH}. Please ensure the model file exists.",
        )

    if hasattr(current_user, "student_id"):
        result = await student_check_in_with_verification(
            db=db,
            attendance_id=attendance_id,
            check_in_data=check_in_data,
            image_file=image_captured_url,
            current_user=current_user,
            model_path=MODEL_PATH,
        )

        if not result["success"]:
            raise HTTPException(status_code=403, detail=result["message"])

        return result["attendance"]

    else:
        image_url = None
        if image_captured_url and image_captured_url.filename:
            upload_dir = "uploads/attendance_images"
            os.makedirs(upload_dir, exist_ok=True)

            if attendance.image_captured_url:
                old_file_path = attendance.image_captured_url.replace(
                    "/uploads/", "uploads/"
                )
                if os.path.exists(old_file_path):
                    os.remove(old_file_path)

            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            file_extension = os.path.splitext(image_captured_url.filename)[1]
            filename = f"attendance_{attendance_id}_{timestamp}{file_extension}"
            file_path = os.path.join(upload_dir, filename)

            content = await image_captured_url.read()
            with open(file_path, "wb") as buffer:
                buffer.write(content)

            image_url = f"/uploads/attendance_images/{filename}"

        updated_attendance = student_check_in(
            db=db,
            attendance_id=attendance_id,
            check_in_data=check_in_data,
            image_captured_url=image_url,
        )

        if updated_attendance is None:
            raise HTTPException(
                status_code=404, detail="Failed to update attendance record"
            )

        return updated_attendance


@router.get("/", response_model=List[AttendanceWithNestedData])
def read_attendances_endpoint(
    skip: int = 0,
    limit: int = 100,
    student_id: int = None,
    schedule_id: int = None,
    course_id: int = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin_or_instructor),
):
    """
    Retrieve all attendance records with nested related data and filtering options.
    Supports pagination and filtering by student_id, schedule_id, or course_id.
    Only accessible by admin and instructor users.
    """
    attendances = get_attendances(
        db,
        skip=skip,
        limit=limit,
        student_id=student_id,
        schedule_id=schedule_id,
        course_id=course_id,
    )
    return attendances


@router.get("/{attendance_id}", response_model=AttendanceRead)
def read_attendance_endpoint(
    attendance_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Retrieve a specific attendance record by ID.
    Students can only view their own attendance records.
    Admin and instructors can view any attendance record.
    """
    attendance = get_attendance(db, attendance_id=attendance_id)
    if attendance is None:
        raise HTTPException(status_code=404, detail="Attendance not found")

    is_admin = getattr(current_user, "role", None) in ["ADMIN", "INSTRUCTOR"]
    is_own_student = (
        hasattr(current_user, "student_id")
        and current_user.student_id == attendance.student_id
    )

    if not (is_admin or is_own_student):
        raise HTTPException(
            status_code=403, detail="You can only view your own attendance records"
        )

    return attendance


@router.get("/student/{student_id}", response_model=List[AttendanceWithNestedData])
def read_student_attendances_endpoint(
    student_id: int,
    schedule_id: int = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Retrieve all attendance records for a specific student with nested data.
    Students can only view their own attendance records.
    Admin and instructors can view any student's attendance records.
    Supports filtering by schedule_id and pagination.
    """
    is_admin = getattr(current_user, "role", None) in ["ADMIN", "INSTRUCTOR"]
    is_own_student = (
        hasattr(current_user, "student_id") and current_user.student_id == student_id
    )

    if not (is_admin or is_own_student):
        raise HTTPException(
            status_code=403, detail="You can only view your own attendance records"
        )

    attendances = get_student_attendances(
        db, student_id=student_id, schedule_id=schedule_id, skip=skip, limit=limit
    )

    return attendances


@router.patch("/{attendance_id}", response_model=AttendanceRead)
def update_attendance_endpoint(
    attendance_id: int,
    attendance: AttendanceUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin_or_instructor),
):
    """
    Update an existing attendance record.
    Only admin and instructor users can update attendance records.
    Automatically adds updated timestamp and processes JSON fields.
    """
    attendance_dict = attendance.dict(exclude_unset=True)
    attendance_dict["updated_at"] = get_indonesia_time()

    if "location_data" in attendance_dict:
        attendance_dict["location_data"] = process_json_field(
            attendance_dict["location_data"]
        )
    if "face_verification_data" in attendance_dict:
        attendance_dict["face_verification_data"] = process_json_field(
            attendance_dict["face_verification_data"]
        )

    attendance = parse_obj_as(AttendanceUpdate, attendance_dict)

    db_attendance = update_attendance(
        db, attendance_id=attendance_id, attendance=attendance
    )
    if db_attendance is None:
        raise HTTPException(status_code=404, detail="Attendance not found")
    return db_attendance


@router.delete("/{attendance_id}")
def delete_attendance_endpoint(
    attendance_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin_or_instructor),
):
    """
    Delete a specific attendance record by ID.
    Only admin and instructor users can delete attendance records.
    """
    success = delete_attendance(db, attendance_id=attendance_id)
    if not success:
        raise HTTPException(status_code=404, detail="Attendance not found")
    return {"message": "Attendance successfully deleted"}


@router.delete("/multiple", response_model=dict)
def delete_multiple_attendances_endpoint(
    data: MultipleAttendanceDelete,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin_or_instructor),
):
    """
    Delete multiple attendance records simultaneously.
    Only admin and instructor users can perform bulk deletion.
    Returns count of successfully deleted records.
    """
    if not data.attendance_ids:
        raise HTTPException(
            status_code=400,
            detail="At least one attendance ID must be provided",
        )

    deleted_count = delete_multiple_attendances(db, attendance_ids=data.attendance_ids)

    return {
        "message": f"Successfully deleted {deleted_count} attendance records",
        "deleted_count": deleted_count,
}


@router.get("/active-schedules", response_model=List)
def get_active_schedules_endpoint(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Retrieve active schedules for the current authenticated student.
    Only accessible by student users for their own active schedules.
    """
    if not hasattr(current_user, "student_id"):
        raise HTTPException(
            status_code=403, detail="Only students can view their active schedules"
        )

    active_schedules = get_active_student_schedule(db, current_user.student_id)
    return active_schedules

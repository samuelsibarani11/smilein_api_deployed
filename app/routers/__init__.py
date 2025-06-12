from fastapi import APIRouter
from .admin import router as admin_router
from .attendance import router as attendance_router
from .course import router as course_router
from .instructor_course import router as instructor_course_router
from .instructor import router as instructor_router
from .schedule import router as schedule_router
from .student import router as student_router
from .room import router as room_router

router = APIRouter()

router.include_router(admin_router)
router.include_router(attendance_router)
router.include_router(course_router)
router.include_router(instructor_course_router)  # Hapus duplikasi admin_router
router.include_router(instructor_router)
router.include_router(schedule_router)
router.include_router(student_router)
router.include_router(room_router)
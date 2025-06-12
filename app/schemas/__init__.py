from .admin import AdminCreate, AdminRead, AdminUpdate
from .attendance import AttendanceCreate, AttendanceRead, AttendanceUpdate
from .course import CourseCreate, CourseUpdate, CourseRead
from .instructor_course import (
    InstructorCourseCreate,
    InstructorCourseRead,
    InstructorCourseUpdate,
)
from .instructor import InstructorCreate, InstructorUpdate
from .schedule import ScheduleBase, ScheduleCreate, ScheduleRead, ScheduleUpdate
from .student import StudentCreate, StudentRead, StudentUpdate
from .room import RoomBase, RoomCreate, RoomResponse, RoomUpdate

__all__ = [
    "AdminCreate",
    "AdminRead",
    "AdminUpdate",
    "AttendanceCreate",
    "AttendanceRead",
    "AttendanceUpdate",
    "CourseCreate",
    "CourseUpdate",
    "CourseRead",
    "InstructorCourseCreate",
    "InstructorCourseRead",
    "InstructorCourseUpdate",
    "InstructorCreate",
    "InstructorUpdate",
    "RoomBase",
    "RoomCreate",
    "RoomResponse",
    "RoomUpdate",
    "ScheduleBase",
    "ScheduleCreate",
    "ScheduleRead",
    "ScheduleUpdate",
    "StudentCreate",
    "StudentRead",
    "StudentUpdate",
]

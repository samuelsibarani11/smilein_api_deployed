# Import all models to make them available from app.models
from app.models.admin import Admin
from app.models.attendance import Attendance
from app.models.course import Course
from app.models.instructor_course import InstructorCourse
from app.models.instructor import Instructor
from app.models.schedule import Schedule
from app.models.student import Student
from app.models.room import Room


# Export all models
__all__ = [
    "Admin",
    "Attendance",
    "Course",
    "InstructorCourse",
    "Instructor",
    "Schedule",
    "Student",
    "Room",
]

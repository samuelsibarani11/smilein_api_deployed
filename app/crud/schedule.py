from datetime import date
from typing import List, Optional

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.course import Course
from app.models.instructor import Instructor
from app.models.room import Room
from app.models.schedule import Schedule
from app.schemas.schedule import ScheduleCreate, ScheduleUpdate
from app.utils.time_utils import get_indonesia_time


def create_schedule(db: Session, schedule: ScheduleCreate) -> Schedule:
    """
    Create a new schedule entry with comprehensive validation.

    This function validates the existence of instructor, course, and room (if provided)
    before creating a new schedule record. It ensures data integrity by checking
    foreign key relationships and automatically sets the creation timestamp.

    Args:
        db (Session): Active database session for executing queries
        schedule (ScheduleCreate): Schedule data containing instructor_id, course_id,
                                 room_id (optional), chapter, schedule_date,
                                 start_time, and end_time

    Returns:
        Schedule: Newly created schedule object with generated ID

    Raises:
        HTTPException: 404 if instructor, course, or room (when provided) not found
    """
    instructor = db.get(Instructor, schedule.instructor_id)
    if not instructor:
        raise HTTPException(
            status_code=404,
            detail=f"Instructor with ID {schedule.instructor_id} not found",
        )

    course = db.get(Course, schedule.course_id)
    if not course:
        raise HTTPException(
            status_code=404, detail=f"Course with ID {schedule.course_id} not found"
        )

    if schedule.room_id:
        room = db.get(Room, schedule.room_id)
        if not room:
            raise HTTPException(
                status_code=404, detail=f"Room with ID {schedule.room_id} not found"
            )

    db_schedule = Schedule(
        instructor_id=schedule.instructor_id,
        course_id=schedule.course_id,
        room_id=schedule.room_id,
        chapter=schedule.chapter,
        schedule_date=schedule.schedule_date,
        start_time=schedule.start_time,
        end_time=schedule.end_time,
        created_at=get_indonesia_time(),
    )

    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)

    return db_schedule


def get_schedules(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    course_id: Optional[int] = None,
    instructor_id: Optional[int] = None,
    room_id: Optional[int] = None,
    schedule_date: Optional[date] = None,
) -> List[dict]:
    """
    Retrieve schedules with comprehensive filtering and joined entity details.

    This function performs a complex query with outer joins to fetch schedule data
    along with related course, instructor, and room information. It supports
    multiple filter options and pagination. The result is formatted as a list
    of dictionaries containing all relevant details for easy consumption.

    Args:
        db (Session): Active database session for executing queries
        skip (int): Number of records to skip for pagination (default: 0)
        limit (int): Maximum number of records to return (default: 100)
        course_id (Optional[int]): Filter schedules by specific course ID
        instructor_id (Optional[int]): Filter schedules by specific instructor ID
        room_id (Optional[int]): Filter schedules by specific room ID
        schedule_date (Optional[date]): Filter schedules by specific date

    Returns:
        List[dict]: List of formatted schedule dictionaries containing schedule
                   details with nested course, instructor, and room information
    """
    query = (
        select(Schedule, Course, Instructor, Room)
        .join(Course, Schedule.course_id == Course.course_id, isouter=True)
        .join(
            Instructor, Schedule.instructor_id == Instructor.instructor_id, isouter=True
        )
        .join(Room, Schedule.room_id == Room.room_id, isouter=True)
    )

    if course_id is not None:
        query = query.where(Schedule.course_id == course_id)
    if instructor_id is not None:
        query = query.where(Schedule.instructor_id == instructor_id)
    if room_id is not None:
        query = query.where(Schedule.room_id == room_id)
    if schedule_date is not None:
        query = query.where(Schedule.schedule_date == schedule_date)

    results = db.exec(query.offset(skip).limit(limit)).all()

    schedules = []
    for schedule, course, instructor, room in results:
        schedules.append(
            {
                "schedule_id": schedule.schedule_id,
                "chapter": schedule.chapter,
                "schedule_date": schedule.schedule_date,
                "start_time": schedule.start_time,
                "end_time": schedule.end_time,
                "created_at": schedule.created_at,
                "course": {
                    "course_id": course.course_id if course else 0,
                    "course_name": course.course_name if course else "Unknown Course",
                },
                "instructor": {
                    "instructor_id": instructor.instructor_id if instructor else 0,
                    "full_name": instructor.full_name
                    if instructor
                    else "Unknown Instructor",
                },
                "room": {
                    "room_id": room.room_id if room else 0,
                    "name": room.name if room else "Unknown Room",
                    "latitude": room.latitude if room else 0.0,
                    "longitude": room.longitude if room else 0.0,
                    "radius": room.radius if room else 0.0,
                }
                if room
                else None,
            }
        )

    return schedules


def get_schedule(db: Session, schedule_id: int) -> Schedule:
    """
    Retrieve a single schedule by its unique identifier.

    This function fetches a specific schedule record from the database using
    the provided schedule ID. It includes error handling for non-existent
    schedules to ensure proper API responses.

    Args:
        db (Session): Active database session for executing queries
        schedule_id (int): Unique identifier of the schedule to retrieve

    Returns:
        Schedule: The schedule object matching the provided ID

    Raises:
        HTTPException: 404 if no schedule found with the given ID
    """
    schedule = db.get(Schedule, schedule_id)
    if schedule is None:
        raise HTTPException(
            status_code=404, detail=f"Schedule with ID {schedule_id} not found"
        )
    return schedule


def update_schedule(
    db: Session, schedule_id: int, schedule: ScheduleUpdate
) -> Schedule:
    """
    Update an existing schedule with partial data validation.

    This function allows partial updates of schedule records by validating only
    the fields that are provided in the update request. It performs existence
    checks for related entities (instructor, course, room) only when their IDs
    are being updated, ensuring data integrity while allowing flexible updates.

    Args:
        db (Session): Active database session for executing queries
        schedule_id (int): Unique identifier of the schedule to update
        schedule (ScheduleUpdate): Partial schedule data with fields to update

    Returns:
        Schedule: Updated schedule object with refreshed data

    Raises:
        HTTPException: 404 if schedule, instructor, course, or room not found
    """
    db_schedule = get_schedule(db, schedule_id)

    if schedule.instructor_id is not None:
        instructor = db.get(Instructor, schedule.instructor_id)
        if not instructor:
            raise HTTPException(
                status_code=404,
                detail=f"Instructor with ID {schedule.instructor_id} not found",
            )

    if schedule.course_id is not None:
        course = db.get(Course, schedule.course_id)
        if not course:
            raise HTTPException(
                status_code=404, detail=f"Course with ID {schedule.course_id} not found"
            )

    if schedule.room_id is not None:
        room = db.get(Room, schedule.room_id)
        if not room:
            raise HTTPException(
                status_code=404, detail=f"Room with ID {schedule.room_id} not found"
            )

    schedule_data = schedule.model_dump(exclude_unset=True)
    for key, value in schedule_data.items():
        setattr(db_schedule, key, value)

    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)

    return db_schedule


def delete_schedule(db: Session, schedule_id: int) -> Schedule:
    """
    Delete a schedule record from the database.

    This function removes a schedule entry permanently from the database.
    It first verifies the schedule exists before attempting deletion to
    ensure proper error handling and returns the deleted record for
    confirmation or logging purposes.

    Args:
        db (Session): Active database session for executing queries
        schedule_id (int): Unique identifier of the schedule to delete

    Returns:
        Schedule: The deleted schedule object for confirmation

    Raises:
        HTTPException: 404 if no schedule found with the given ID
    """
    db_schedule = get_schedule(db, schedule_id)
    db.delete(db_schedule)
    db.commit()
    return db_schedule


def check_schedule_conflict(
    db: Session,
    room_id: int,
    schedule_date: date,
    start_time: str,
    end_time: str,
    schedule_id: Optional[int] = None,
) -> bool:
    """
    Detect scheduling conflicts for room bookings with time overlap logic.

    This function implements comprehensive conflict detection by checking if a new
    or updated schedule overlaps with existing schedules in the same room on the
    same date. It uses three overlap conditions: new schedule starts during existing,
    new schedule ends during existing, or new schedule completely contains existing.
    When updating an existing schedule, it excludes the current schedule from
    conflict checking to prevent self-conflict detection.

    Args:
        db (Session): Active database session for executing queries
        room_id (int): ID of the room to check for scheduling conflicts
        schedule_date (date): Date on which to check for conflicts
        start_time (str): Start time of the proposed schedule
        end_time (str): End time of the proposed schedule
        schedule_id (Optional[int]): ID of current schedule to exclude from
                                   conflict check (used during updates)

    Returns:
        bool: True if a scheduling conflict exists, False if the time slot is available
    """
    query = select(Schedule).where(
        Schedule.room_id == room_id,
        Schedule.schedule_date == schedule_date,
        ((Schedule.start_time <= start_time) & (Schedule.end_time > start_time))
        | ((Schedule.start_time < end_time) & (Schedule.end_time >= end_time))
        | ((Schedule.start_time >= start_time) & (Schedule.end_time <= end_time)),
    )

    if schedule_id is not None:
        query = query.where(Schedule.schedule_id != schedule_id)

    result = db.exec(query).first()
    return result is not None

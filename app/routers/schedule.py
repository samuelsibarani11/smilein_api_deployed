from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List, Optional
from datetime import date

from app.dependencies import get_db, get_current_admin_or_instructor
from app.schemas.schedule import ScheduleCreate, ScheduleRead, ScheduleUpdate
from app.crud.schedule import (
    create_schedule,
    get_schedules,
    get_schedule,
    update_schedule,
    delete_schedule,
    check_schedule_conflict,
)

# Access Control: ADMIN | INSTRUCTOR
# - Instructor can only manage their own schedules
# - Admin can manage all schedules

router = APIRouter(
    prefix="/schedules",
    tags=["schedules"],
    responses={404: {"description": "Not found"}},
)


@router.post("/", response_model=ScheduleRead, status_code=status.HTTP_201_CREATED)
def create_schedule_endpoint(
    schedule: ScheduleCreate,
    db: Session = Depends(get_db),
    user_data=Depends(get_current_admin_or_instructor),
):
    """
    Create a new schedule entry in the system.

    This endpoint allows authorized users to create new schedules with proper
    access control and conflict validation. Instructors can only create schedules
    for themselves, while admins can create schedules for any instructor.
    Room conflicts are automatically checked when a room is specified.

    Args:
        schedule: Schedule data including course, instructor, room, date and time
        db: Database session dependency
        user_data: Current authenticated user information

    Returns:
        ScheduleRead: Created schedule with all details

    Raises:
        HTTPException: 403 if instructor tries to create schedule for others
        HTTPException: 400 if schedule conflict is detected
    """
    user = user_data["user"]
    user_type = user_data["user_type"]

    # Enforce instructor access control - can only create own schedules
    if user_type == "instructor" and schedule.instructor_id != user.instructor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only create schedules for yourself",
        )

    # Validate room availability if room is specified
    if schedule.room_id:
        if check_schedule_conflict(
            db=db,
            room_id=schedule.room_id,
            schedule_date=schedule.schedule_date,
            start_time=schedule.start_time,
            end_time=schedule.end_time,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Schedule conflict detected. The room is already scheduled for this time.",
            )

    return create_schedule(db=db, schedule=schedule)


@router.get("/", response_model=List[ScheduleRead])
def read_schedules_endpoint(
    skip: int = 0,
    limit: int = 100,
    course_id: Optional[int] = None,
    instructor_id: Optional[int] = None,
    room_id: Optional[int] = None,
    schedule_date: Optional[date] = None,
    db: Session = Depends(get_db),
    user_data=Depends(get_current_admin_or_instructor),
):
    """
    Retrieve schedules with optional filtering and pagination.

    This endpoint provides filtered access to schedule data based on user role.
    Instructors can only view their own schedules, while admins can view all
    schedules. Multiple filters can be applied simultaneously for refined results.

    Args:
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        course_id: Filter by specific course ID
        instructor_id: Filter by specific instructor ID
        room_id: Filter by specific room ID
        schedule_date: Filter by specific date
        db: Database session dependency
        user_data: Current authenticated user information

    Returns:
        List[ScheduleRead]: List of schedules matching the criteria

    Raises:
        HTTPException: 403 if instructor tries to access other instructor's schedules
    """
    user = user_data["user"]
    user_type = user_data["user_type"]

    # Apply instructor-specific access restrictions
    if user_type == "instructor":
        # Prevent instructors from viewing other instructor's schedules
        if instructor_id is not None and instructor_id != user.instructor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own schedules",
            )
        # Force filter to show only instructor's own schedules
        instructor_id = user.instructor_id

    schedules = get_schedules(
        db,
        skip=skip,
        limit=limit,
        course_id=course_id,
        instructor_id=instructor_id,
        room_id=room_id,
        schedule_date=schedule_date,
    )
    return schedules


@router.get("/{schedule_id}", response_model=ScheduleRead)
def read_schedule_endpoint(
    schedule_id: int,
    db: Session = Depends(get_db),
    user_data=Depends(get_current_admin_or_instructor),
):
    """
    Retrieve a specific schedule by its unique identifier.

    This endpoint fetches detailed information about a single schedule entry.
    Access control ensures instructors can only view their own schedules,
    while admins have unrestricted access to all schedule records.

    Args:
        schedule_id: Unique identifier of the schedule to retrieve
        db: Database session dependency
        user_data: Current authenticated user information

    Returns:
        ScheduleRead: Complete schedule information

    Raises:
        HTTPException: 404 if schedule not found
        HTTPException: 403 if instructor tries to access other instructor's schedule
    """
    schedule = get_schedule(db, schedule_id=schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")

    user = user_data["user"]
    user_type = user_data["user_type"]

    # Enforce instructor access control for individual schedule viewing
    if user_type == "instructor" and schedule.instructor_id != user.instructor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own schedules",
        )

    return schedule


@router.patch("/{schedule_id}", response_model=ScheduleRead)
def update_schedule_endpoint(
    schedule_id: int,
    schedule_update: ScheduleUpdate,
    db: Session = Depends(get_db),
    user_data=Depends(get_current_admin_or_instructor),
):
    """
    Update an existing schedule with new information.

    This endpoint allows partial updates to schedule records with comprehensive
    validation. Instructors can only modify their own schedules and cannot
    reassign schedules to other instructors. Room conflicts are checked when
    time, date, or room changes are attempted.

    Args:
        schedule_id: Unique identifier of the schedule to update
        schedule_update: Partial schedule data for updates
        db: Database session dependency
        user_data: Current authenticated user information

    Returns:
        ScheduleRead: Updated schedule with all current information

    Raises:
        HTTPException: 404 if schedule not found
        HTTPException: 403 if instructor tries to update other instructor's schedule
        HTTPException: 403 if instructor tries to reassign schedule to others
        HTTPException: 400 if schedule conflict is detected
    """
    existing_schedule = get_schedule(db, schedule_id=schedule_id)
    if existing_schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")

    user = user_data["user"]
    user_type = user_data["user_type"]

    # Verify instructor can only update their own schedules
    if (
        user_type == "instructor"
        and existing_schedule.instructor_id != user.instructor_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own schedules",
        )

    # Prevent instructors from reassigning schedules to other instructors
    if schedule_update.instructor_id is not None:
        if (
            user_type == "instructor"
            and schedule_update.instructor_id != user.instructor_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot assign schedules to other instructors",
            )

    # Check for scheduling conflicts when time/room related fields are updated
    if (
        schedule_update.room_id is not None
        or schedule_update.schedule_date is not None
        or schedule_update.start_time is not None
        or schedule_update.end_time is not None
    ):
        # Use updated values where provided, otherwise keep existing values
        room_id = (
            schedule_update.room_id
            if schedule_update.room_id is not None
            else existing_schedule.room_id
        )
        date_value = (
            schedule_update.schedule_date
            if schedule_update.schedule_date is not None
            else existing_schedule.schedule_date
        )
        start_time = (
            schedule_update.start_time
            if schedule_update.start_time is not None
            else existing_schedule.start_time
        )
        end_time = (
            schedule_update.end_time
            if schedule_update.end_time is not None
            else existing_schedule.end_time
        )

        # Validate no conflicts exist with the updated schedule
        if room_id and check_schedule_conflict(
            db=db,
            room_id=room_id,
            schedule_date=date_value,
            start_time=start_time,
            end_time=end_time,
            schedule_id=schedule_id,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Schedule conflict detected. The room is already scheduled for this time.",
            )

    db_schedule = update_schedule(db, schedule_id=schedule_id, schedule=schedule_update)
    return db_schedule


@router.delete("/{schedule_id}")
def delete_schedule_endpoint(
    schedule_id: int,
    db: Session = Depends(get_db),
    user_data=Depends(get_current_admin_or_instructor),
):
    """
    Delete a schedule record from the system.

    This endpoint permanently removes a schedule entry with proper access control.
    Instructors can only delete their own schedules, while admins can delete
    any schedule. The operation returns a confirmation message upon success.

    Args:
        schedule_id: Unique identifier of the schedule to delete
        db: Database session dependency
        user_data: Current authenticated user information

    Returns:
        dict: Success message confirming deletion

    Raises:
        HTTPException: 404 if schedule not found
        HTTPException: 403 if instructor tries to delete other instructor's schedule
    """
    existing_schedule = get_schedule(db, schedule_id=schedule_id)
    if existing_schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")

    user = user_data["user"]
    user_type = user_data["user_type"]

    # Ensure instructors can only delete their own schedules
    if (
        user_type == "instructor"
        and existing_schedule.instructor_id != user.instructor_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own schedules",
        )

    success = delete_schedule(db, schedule_id=schedule_id)
    if not success:
        raise HTTPException(status_code=404, detail="Schedule not found")

    return {"message": "Schedule successfully deleted"}

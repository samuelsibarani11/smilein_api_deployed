from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.room import Room
from app.schemas.room import RoomCreate, RoomUpdate


def create_room(db: Session, room: RoomCreate) -> Room:
    """
    Create a new room with location and radius configuration.

    Creates a room with geographical coordinates and geofencing radius for
    attendance tracking purposes. Room data is validated before creation
    and committed to database with automatic ID generation.

    Args:
        db: Database session for transaction management
        room: Validated room creation data including name and location

    Returns:
        Room: Newly created room with generated ID and all attributes

    Raises:
        SQLAlchemyError: If database operation fails
        IntegrityError: If room name already exists
    """
    db_room = Room(
        name=room.name,
        latitude=room.latitude,
        longitude=room.longitude,
        radius=room.radius,
    )

    db.add(db_room)
    db.commit()
    db.refresh(db_room)

    return db_room


def get_rooms(
    db: Session, skip: int = 0, limit: int = 100, name: str | None = None
) -> list[Room]:
    """
    Retrieve rooms with pagination and optional name filtering.

    Fetches rooms with support for pagination and case-insensitive name search.
    Name filter uses ILIKE for partial matching, allowing flexible room discovery.
    Results are ordered by default database ordering for consistent pagination.

    Args:
        db: Database session for query execution
        skip: Number of records to skip for pagination (default: 0)
        limit: Maximum number of records to return (default: 100)
        name: Optional partial name filter for room search

    Returns:
        list[Room]: List of rooms matching criteria
    """
    query = select(Room)

    if name:
        query = query.where(Room.name.ilike(f"%{name}%"))

    rooms = db.exec(query.offset(skip).limit(limit)).all()
    return rooms


def get_room(db: Session, room_id: int) -> Room:
    """
    Retrieve a specific room by ID with validation.

    Fetches a single room using primary key lookup and validates existence.
    Raises HTTP 404 exception if room not found to maintain API consistency
    and provide clear error messaging for client applications.

    Args:
        db: Database session for query execution
        room_id: Unique identifier of the room

    Returns:
        Room: The requested room with all attributes

    Raises:
        HTTPException: 404 error if room not found
    """
    room = db.get(Room, room_id)
    if room is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room with ID {room_id} not found",
        )
    return room


def update_room(db: Session, room_id: int, room: RoomUpdate) -> Room:
    """
    Update an existing room's information.

    Performs partial update of room data including location coordinates and radius.
    Validates room existence before update and uses exclude_unset to update only
    provided fields, maintaining existing values for unchanged attributes.

    Args:
        db: Database session for transaction management
        room_id: ID of room to update
        room: Partial room data for update

    Returns:
        Room: Updated room with refreshed data

    Raises:
        HTTPException: 404 error if room not found
        SQLAlchemyError: If database operation fails
    """
    db_room = get_room(db, room_id)

    room_data = room.model_dump(exclude_unset=True)
    for key, value in room_data.items():
        setattr(db_room, key, value)

    db.add(db_room)
    db.commit()
    db.refresh(db_room)

    return db_room


def delete_room(db: Session, room_id: int) -> Room:
    """
    Delete a room with schedule dependency validation.

    Safely removes room from database after checking for active schedule
    dependencies. Prevents deletion of rooms currently in use to maintain
    data integrity and prevent orphaned schedule records.

    Args:
        db: Database session for transaction management
        room_id: ID of room to delete

    Returns:
        Room: The deleted room for confirmation purposes

    Raises:
        HTTPException: 404 error if room not found
        HTTPException: 400 error if room has associated schedules
        SQLAlchemyError: If database operation fails
    """
    db_room = get_room(db, room_id)
    if db_room.schedules and len(db_room.schedules) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Room with ID {room_id} cannot be deleted because it is currently in use (has associated schedules)",
        )
    db.delete(db_room)
    db.commit()
    return db_room

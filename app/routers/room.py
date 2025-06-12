from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List, Optional

from app.dependencies import get_db, get_current_admin
from app.schemas.room import RoomCreate, RoomResponse, RoomUpdate
from app.crud.room import create_room, get_rooms, get_room, update_room, delete_room


router = APIRouter(
    prefix="/rooms",
    tags=["rooms"],
    responses={404: {"description": "Not found"}},
)


@router.post("/", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
def create_room_endpoint(
    room: RoomCreate,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """
    Create a new room in the system.

    This endpoint allows administrators to add new rooms that can be used for
    scheduling classes, meetings, or other educational activities. Each room
    has unique identifiers and capacity information for proper resource management.

    Args:
        room: Room creation data including name, capacity, and location details
        db: Database session dependency
        current_admin: Current authenticated admin user

    Returns:
        RoomResponse: The newly created room with generated ID and details

    Access Level: ADMIN only
    """
    return create_room(db=db, room=room)


@router.get("/", response_model=List[RoomResponse])
def read_rooms_endpoint(
    skip: int = 0,
    limit: int = 100,
    name: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Retrieve all rooms with optional filtering and pagination.

    This public endpoint allows users to browse available rooms in the system.
    It supports filtering by room name and pagination for large datasets.
    Useful for room selection during scheduling or reservation processes.

    Args:
        skip: Number of records to skip for pagination (default: 0)
        limit: Maximum number of records to return (default: 100)
        name: Optional filter to search rooms by name
        db: Database session dependency

    Returns:
        List[RoomResponse]: List of rooms matching the search criteria

    Access Level: PUBLIC
    """
    rooms = get_rooms(db, skip=skip, limit=limit, name=name)
    return rooms


@router.get("/{room_id}", response_model=RoomResponse)
def read_room_endpoint(
    room_id: int,
    db: Session = Depends(get_db),
):
    """
    Retrieve detailed information about a specific room.

    This public endpoint provides comprehensive details about a room including
    its capacity, location, equipment, and availability status. Essential for
    users who need to verify room specifications before making reservations.

    Args:
        room_id: Unique identifier of the room to retrieve
        db: Database session dependency

    Returns:
        RoomResponse: Detailed room information and specifications

    Raises:
        HTTPException: 404 if room is not found (handled by CRUD layer)

    Access Level: PUBLIC
    """
    room = get_room(db, room_id=room_id)
    return room


@router.patch("/{room_id}", response_model=RoomResponse)
def update_room_endpoint(
    room_id: int,
    room_update: RoomUpdate,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """
    Update an existing room's information.

    This endpoint allows administrators to modify room details such as capacity,
    equipment, location, or availability status. Essential for maintaining
    accurate room information and adapting to facility changes or renovations.

    Args:
        room_id: Unique identifier of the room to update
        room_update: Updated room data with modified fields
        db: Database session dependency
        current_admin: Current authenticated admin user

    Returns:
        RoomResponse: The updated room information

    Raises:
        HTTPException: 404 if room is not found (handled by CRUD layer)

    Access Level: ADMIN only
    """
    db_room = update_room(db, room_id=room_id, room=room_update)
    return db_room


@router.delete("/{room_id}")
def delete_room_endpoint(
    room_id: int,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """
    Delete a room from the system.

    This endpoint allows administrators to permanently remove rooms that are
    no longer available or needed. This action should be used carefully as it
    may affect existing schedules, reservations, and class assignments that
    reference this room.

    Args:
        room_id: Unique identifier of the room to delete
        db: Database session dependency
        current_admin: Current authenticated admin user

    Returns:
        dict: Success message confirming deletion

    Raises:
        HTTPException: 404 if room is not found

    Access Level: ADMIN only
    """
    success = delete_room(db, room_id=room_id)
    if not success:
        raise HTTPException(status_code=404, detail="Room not found")
    return {"message": "Room successfully deleted"}

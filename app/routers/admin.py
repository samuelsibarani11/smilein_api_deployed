import os
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlmodel import Session

from app.dependencies import (
    get_current_admin,
    get_current_user_data,
    get_db,
)
from app.schemas.admin import AdminCreate, AdminRead, AdminUpdate, AdminChangePassword
from app.crud.admin import (
    create_admin,
    get_admin_by_username,
    get_admins,
    get_admin,
    update_admin,
    delete_admin,
    change_admin_password,
)
from app.utils.time_utils import get_indonesia_time


router = APIRouter(
    prefix="/admins",
    tags=["admins"],
)


@router.post("/", response_model=AdminRead)
def create_admin_endpoint(
    admin: AdminCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new admin user in the system.
    Accepts admin data and returns the created admin information.
    """
    return create_admin(db=db, admin=admin)


@router.get("/", response_model=List[AdminRead])
def read_admins_endpoint(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """
    Retrieve a list of all admin users with pagination support.
    Requires admin authentication. Returns paginated admin list.
    """
    admins = get_admins(db, skip=skip, limit=limit)
    return admins


@router.get("/{admin_id}", response_model=AdminRead)
def read_admin_endpoint(
    admin_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """
    Retrieve specific admin details by ID.
    Requires admin authentication. Returns admin data or 404 if not found.
    """
    admin = get_admin(db, admin_id=admin_id)
    if admin is None:
        raise HTTPException(status_code=404, detail="Admin tidak ditemukan")
    return admin


@router.patch("/{admin_id}", response_model=AdminRead)
def update_admin_endpoint(
    admin_id: int,
    admin: AdminUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """
    Update existing admin information by ID.
    Requires admin authentication. Returns updated admin data or 404 if not found.
    """
    db_admin = update_admin(db, admin_id=admin_id, admin=admin)
    if db_admin is None:
        raise HTTPException(status_code=404, detail="Admin tidak ditemukan")
    return db_admin


@router.delete("/{admin_id}")
def delete_admin_endpoint(
    admin_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """
    Delete an admin user by ID.
    Requires admin authentication. Returns success message or 404 if not found.
    """
    success = delete_admin(db, admin_id=admin_id)
    if not success:
        raise HTTPException(status_code=404, detail="Admin tidak ditemukan")
    return {"message": "Admin berhasil dihapus"}


@router.post("/{admin_id}/profile-picture", response_model=AdminRead)
async def upload_admin_profile_picture_endpoint(
    admin_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user_data=Depends(get_current_user_data),
):
    """
    Upload and update admin profile picture.
    Only admin can upload profile pictures, and they can only modify their own
    (except super admin who can modify any). Validates file type, removes old
    picture if exists, saves new file with timestamp, and updates database.
    """
    user = current_user_data["user"]
    user_type = current_user_data["user_type"]

    if user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can perform this action",
        )

    if user.admin_id != admin_id and user.admin_id != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only modify your own profile picture",
        )

    db_admin = get_admin(db, admin_id=admin_id)
    if db_admin is None:
        raise HTTPException(status_code=404, detail="Admin not found")

    valid_content_types = ["image/jpeg", "image/png", "image/gif", "image/jpg"]
    if file.content_type not in valid_content_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image (JPEG, PNG, or GIF)",
        )

    upload_dir = "uploads/admin_profile_pictures"
    os.makedirs(upload_dir, exist_ok=True)

    if db_admin.profile_picture_url:
        old_file_path = db_admin.profile_picture_url.replace("/uploads/", "uploads/")
        if os.path.exists(old_file_path):
            os.remove(old_file_path)

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    file_extension = os.path.splitext(file.filename)[1]
    filename = f"admin_{admin_id}_{timestamp}{file_extension}"
    file_path = os.path.join(upload_dir, filename)

    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    profile_picture_url = f"/uploads/admin_profile_pictures/{filename}"

    db_admin.profile_picture_url = profile_picture_url
    db_admin.updated_at = get_indonesia_time()
    db.add(db_admin)
    db.commit()
    db.refresh(db_admin)

    return db_admin


@router.get("/{admin_id}/profile-picture")
def get_admin_profile_picture_endpoint(
    admin_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """
    Retrieve admin profile picture URL by ID.
    Requires admin authentication. Returns profile picture URL or 404 if admin
    or picture not found.
    """
    admin = get_admin(db, admin_id=admin_id)
    if admin is None:
        raise HTTPException(status_code=404, detail="Admin not found")

    if not admin.profile_picture_url:
        raise HTTPException(status_code=404, detail="Profile picture not found")

    return {"profile_picture_url": admin.profile_picture_url}


@router.get("/instructors/{username}", response_model=AdminRead)
def get_instructor(username: str, db: Session = Depends(get_db)):
    """
    Retrieve instructor (admin) information by username.
    Returns instructor data or 404 if not found. No authentication required.
    """
    instructor = get_admin_by_username(db, username)
    if not instructor:
        raise HTTPException(status_code=404, detail="Instructor not found")
    return instructor


@router.post("/change-password")
def change_password_endpoint(
    password_data: AdminChangePassword,
    db: Session = Depends(get_db),
    current_user_data=Depends(get_current_user_data),
):
    """
    Change current admin's password.
    Requires admin authentication, validates current password, confirms new
    password matches confirmation, and updates password in database.
    """
    user = current_user_data["user"]
    user_type = current_user_data["user_type"]

    if user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can perform this action",
        )

    if password_data.new_password != password_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password and confirmation do not match",
        )

    result = change_admin_password(
        db=db,
        admin_id=user.admin_id,
        current_password=password_data.current_password,
        new_password=password_data.new_password,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found"
        )
    elif result is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    return {"message": "Password successfully changed"}

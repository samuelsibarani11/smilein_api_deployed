from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session

from app.dependencies import get_db, get_current_user_data
from app.schemas.token import Token
from app.schemas.auth import ChangePasswordRequest
from app.services.auth_service import login_user, change_password


router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
)


@router.post("/token", response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """
    Authenticate user and generate access token.
    OAuth2 compatible token login endpoint that accepts username and password,
    validates credentials, and returns JWT access token with user information.
    """
    token_data = login_user(
        db=db, username=form_data.username, password=form_data.password
    )

    return {
        "access_token": token_data["access_token"],
        "token_type": token_data["token_type"],
        "user_type": token_data["user_type"],
        "user_id": token_data["user_id"],
    }


@router.post("/change-password")
def change_password_endpoint(
    request: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user_data=Depends(get_current_user_data),
):
    """
    Change password for authenticated users.
    Validates current password, confirms new password matches confirmation,
    and updates password for any authenticated user type (admin, instructor, student).
    Automatically determines user type and ID from authentication context.
    """
    user = current_user_data["user"]
    user_type = current_user_data["user_type"]

    id_field_name = f"{user_type}_id"
    user_id = getattr(user, id_field_name)

    if request.new_password != request.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password and confirmation do not match",
        )

    success = change_password(
        db=db,
        user_type=user_type,
        user_id=user_id,
        current_password=request.current_password,
        new_password=request.new_password,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect or user not found",
        )

    return {"message": "Password successfully changed"}

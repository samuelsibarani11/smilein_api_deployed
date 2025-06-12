from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session
import uvicorn
from app.routers import router
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from app.dependencies import create_db_and_tables, get_db, ACCESS_TOKEN_EXPIRE_MINUTES
import os
from datetime import  timedelta


# Import authentication-related functions
from app.utils.authentication import (
    authenticate,
    create_access_token,
)

# Create FastAPI app
app = FastAPI(
    title="SmileIn Management API",
    description="An API for managing items with FastAPI, SQLModel, and SQLite",
    version="1.0.0",
)

origins = [
    "http://localhost:5173",
]

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "OPTIONS",
    ],
    allow_headers=[
        "Content-Type",
        "Set-Cookie",
        "Access-Control-Allow-Headers",
        "Access-Control-Allow-Origin",
        "Authorization",
    ],
)
os.makedirs("uploads/admin_profile_pictures", exist_ok=True)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Create the uploads directory if it doesn't exist
os.makedirs("uploads/attendance_images", exist_ok=True)

# Mount the uploads directory
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# Event handler to create database and tables on startup
@app.on_event("startup")
def on_startup():
    create_db_and_tables()


# Define TokenResponse model with user_type field
class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user_type: str


@app.post("/token", response_model=TokenResponse)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """
    Unified OAuth2 compatible token login endpoint.
    Works for both students and instructors.
    """
    try:
        print("Login attempt:", form_data.username)

        # Try to authenticate as either student or instructor
        user, user_type = authenticate(db, form_data.username, form_data.password)
        print(f"Authenticated as {user_type}:", user)

        # Get the appropriate ID based on user type
        if user_type == "student":
            user_id = user.student_id
        elif user_type == "instructor":
            user_id = user.instructor_id
        elif user_type == "admin":
            user_id = user.admin_id
        else:
            user_id = None

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username},
            expires_delta=access_token_expires,
            user_type=user_type,
            user_id=user_id,
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_type": user_type,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}",
        )


@app.get("/")
async def root():
    return {
        "message": "Welcome to the Item Management API. Visit /docs for API documentation."
    }


app.include_router(router)


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
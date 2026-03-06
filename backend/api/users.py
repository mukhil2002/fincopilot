# backend/api/users.py

from fastapi import APIRouter, Depends
from backend.auth import get_current_user

router = APIRouter()


@router.get("/api/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """
    GET /api/me
    
    Returns the logged-in user's profile.
    If token is missing or invalid, get_current_user() blocks it with 401.
    If token is valid, we just return the user's basic info.
    """
    return {
        "user_id": current_user["id"],
        "email": current_user["email"],
        "created_at": current_user.get("created_at"),
    }
# backend/api/auth.py

from fastapi import APIRouter, Depends
from backend.auth import get_current_user

router = APIRouter()


@router.post("/api/auth/verify")
async def verify_token(current_user: dict = Depends(get_current_user)):
    """
    POST /api/auth/verify
    
    Tests if a token is valid.
    If it reaches this line, the token already passed get_current_user().
    If the token was bad, get_current_user() already returned 401.
    """
    return {
        "valid": True,
        "user_id": current_user["id"],
        "email": current_user["email"],
    }
# backend/auth.py

import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

# HTTPBearer tells FastAPI: expect an Authorization: Bearer <token> header
# auto_error=False means WE handle the missing token error (cleaner message)
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    FastAPI dependency. Add this to any endpoint to make it protected.
    If the token is missing or invalid, this raises a 401 automatically.
    If the token is valid, it returns the user's data as a dict.
    """

    # No token provided at all
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authentication token provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # Send token to Supabase to verify it
    # Supabase has a /auth/v1/user endpoint that validates JWTs
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{SUPABASE_URL}/auth/v1/user",
            headers={
                "Authorization": f"Bearer {token}",
                "apikey": SUPABASE_ANON_KEY,
            },
        )

    # Supabase returns 200 if valid, 401 if not
    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Return the user data (id, email, etc.)
    return response.json()
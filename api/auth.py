from fastapi import APIRouter, HTTPException
import asyncio
from typing import Dict, Any

from core.supabase_sync import supabase_sync
from core.logger import log

router = APIRouter(prefix="/auth", tags=["auth"])

@router.get("/status")
async def get_auth_status() -> Dict[str, Any]:
    """Get the current authentication status and user profile."""
    is_logged_in = supabase_sync.is_logged_in()
    return {
        "is_logged_in": is_logged_in,
        "email": supabase_sync.get_user_email(),
        "display_name": supabase_sync.get_user_display_name(),
        "avatar_url": supabase_sync.get_user_avatar_url(),
    }

@router.post("/login")
async def login() -> Dict[str, Any]:
    """Trigger the Google OAuth login flow."""
    # login_with_google is a blocking function (starts HTTP server, opens browser, waits for callback)
    # We must run it in a thread so it doesn't block the FastAPI event loop
    success = await asyncio.to_thread(supabase_sync.login_with_google)
    if success:
        return {"status": "success", "message": "Login successful"}
    else:
        raise HTTPException(status_code=400, detail="Login failed or was cancelled")

@router.post("/logout")
async def logout() -> Dict[str, Any]:
    """Log out the current user."""
    supabase_sync.logout()
    return {"status": "success", "message": "Logged out successfully"}

# backend/app/core/security.py
from fastapi import Header, HTTPException
from app.services.supabase import get_supabase_client


async def get_current_user(authorization: str = Header(None)):
    """
    Dependency that validates the Supabase JWT from the Header.
    Returns both user object and token for authenticated client creation.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization Header")
    
    token = authorization.replace("Bearer ", "")
    supabase = get_supabase_client()
    
    user_resp = supabase.auth.get_user(token)
    if not user_resp or not user_resp.user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Return both user and token - token needed for authenticated DB queries
    return {"user": user_resp.user, "token": token}
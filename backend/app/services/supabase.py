from fastapi import HTTPException
from supabase import create_client, Client
from app.core.config import settings


def get_authenticated_client(token: str) -> Client:
    """
    Creates a Supabase client with the user's JWT.
    This allows RLS to correctly identify auth.uid().
    """
    client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    # This is the critical part - sets the JWT for PostgREST requests
    client.postgrest.auth(token) 
    return client


def get_supabase_client() -> Client:
    """Get unauthenticated Supabase client instance."""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

async def get_party_id_by_name(supabase, owner_id: str, name: str):
    """
    Utility to resolve a Party Name or Alias into a UUID.
    """
    try:
        # .ilike handles case-insensitive matching
        # .cs.{} handles 'contains' for the Postgres Array (aliases)
        response = supabase.table("parties") \
            .select("id") \
            .eq("owner_id", owner_id) \
            .or_(f"name.ilike.%{name}%,aliases.cs.{{{name}}}") \
            .limit(1) \
            .execute()
        
        if not response.data:
            raise HTTPException(
                status_code=404, 
                detail=f"Party with name '{name}' not found."
            )
        return response.data[0]["id"]
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
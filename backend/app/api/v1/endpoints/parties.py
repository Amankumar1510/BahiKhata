# backend/app/api/v1/endpoints/parties.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.core.security import get_current_user
from app.services.supabase import get_authenticated_client
from app.models.party import PartyCreate, PartyResponse

router = APIRouter()


@router.post("/", response_model=PartyResponse)
async def create_party(
    party: PartyCreate,
    auth_data=Depends(get_current_user)
):
    """
    Create a new Customer or Supplier.
    The owner_id is automatically taken from the logged-in user's token.
    """
    current_user = auth_data["user"]
    token = auth_data["token"]
    
    # Use authenticated client so RLS can identify the user via auth.uid()
    supabase = get_authenticated_client(token)
    
    # Prepare data for Supabase
    new_party = party.model_dump()
    new_party["owner_id"] = current_user.id
    
    try:
        response = supabase.table("parties").insert(new_party).execute()
        return response.data[0]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create party: {str(e)}"
        )


@router.get("/", response_model=List[PartyResponse])
async def list_parties(auth_data=Depends(get_current_user)):
    """
    Fetch all parties belonging to the logged-in user.
    """
    current_user = auth_data["user"]
    token = auth_data["token"]
    
    # Use authenticated client so RLS policies work correctly
    supabase = get_authenticated_client(token)
    
    try:
        # RLS in Supabase will also enforce this, but we filter explicitly for clarity
        response = supabase.table("parties").select("*").eq("owner_id", current_user.id).execute()
        return response.data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.put("/{party_id}", response_model=PartyResponse)
async def update_party(
    party_id: str,
    party_update: PartyCreate, # Reusing PartyCreate for simplicity
    auth_data=Depends(get_current_user)
):
    """
    Update an existing party's details (name, aliases, phone, etc.)
    """
    current_user = auth_data["user"]
    token = auth_data["token"]
    supabase = get_authenticated_client(token)
    
    try:
        response = supabase.table("parties") \
            .update(party_update.model_dump()) \
            .eq("id", party_id) \
            .eq("owner_id", current_user.id) \
            .execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Party not found or unauthorized")
            
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{party_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_party(
    party_id: str,
    auth_data=Depends(get_current_user)
):
    """
    Remove a party and all associated history.
    """
    current_user = auth_data["user"]
    token = auth_data["token"]
    supabase = get_authenticated_client(token)
    
    try:
        response = supabase.table("parties") \
            .delete() \
            .eq("id", party_id) \
            .eq("owner_id", current_user.id) \
            .execute()
            
        if not response.data:
            raise HTTPException(status_code=404, detail="Party not found or unauthorized")
            
        return None # 204 No Content doesn't return a body
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
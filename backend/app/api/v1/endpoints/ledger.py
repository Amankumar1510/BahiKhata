from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.core.security import get_current_user
from app.services.supabase import get_authenticated_client, get_party_id_by_name
from app.models.transaction import TransactionCreate, TransactionResponse

router = APIRouter()

@router.post("/", response_model=TransactionResponse)
async def add_ledger_entry(
    transaction: TransactionCreate, 
    auth_data = Depends(get_current_user)
):
    """Adds a Give/Got entry and returns the calculated amount."""
    token = auth_data["token"]
    user = auth_data["user"]
    supabase = get_authenticated_client(token)
    
    p_id = transaction.party_id
    # Use the service logic to resolve name if ID is missing
    if not p_id and transaction.party_name:
        p_id = await get_party_id_by_name(supabase, user.id, transaction.party_name)
    elif not p_id:
        raise HTTPException(status_code=400, detail="Either party_id or party_name is required")
    
    # Exclude party_name (not in DB) and set resolved party_id
    data = transaction.model_dump(exclude={"party_name"})
    data["party_id"] = p_id
    data["owner_id"] = user.id
    # Convert datetime to ISO string for Postgres
    data["transaction_date"] = data["transaction_date"].isoformat()
    
    try:
        response = supabase.table("transactions").insert(data).execute()
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ledger error: {str(e)}")


# IMPORTANT: This must come BEFORE /{party_id} to avoid route conflict
@router.get("/history", response_model=List[TransactionResponse])
async def get_ledger_by_name(
    name: str,
    auth_data = Depends(get_current_user)
):
    """Fetch history using the Party Name instead of UUID."""
    token = auth_data["token"]
    user = auth_data["user"]
    supabase = get_authenticated_client(token)
    
    # Resolve the name to an ID first
    p_id = await get_party_id_by_name(supabase, user.id, name)
    
    response = supabase.table("transactions") \
        .select("*") \
        .eq("party_id", p_id) \
        .order("transaction_date", desc=True) \
        .execute()
    return response.data


@router.get("/{party_id}", response_model=List[TransactionResponse])
async def get_party_ledger(
    party_id: str, 
    auth_data = Depends(get_current_user)
):
    """Fetches full transaction history for a specific customer/supplier."""
    token = auth_data["token"]
    supabase = get_authenticated_client(token)
    
    try:
        response = supabase.table("transactions") \
            .select("*") \
            .eq("party_id", party_id) \
            .order("transaction_date", desc=True) \
            .execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{transaction_id}", response_model=TransactionResponse)
async def update_ledger_entry(
    transaction_id: str,
    transaction_update: TransactionCreate,
    auth_data = Depends(get_current_user)
):
    """Updates an existing transaction and auto-corrects the party balance."""
    token = auth_data["token"]
    user = auth_data["user"]
    supabase = get_authenticated_client(token)
    
    # Check if transaction exists and belongs to user
    existing = supabase.table("transactions").select("owner_id").eq("id", transaction_id).single().execute()
    if not existing.data or existing.data["owner_id"] != user.id:
        raise HTTPException(status_code=404, detail="Transaction not found")

    update_data = transaction_update.model_dump(exclude={"party_name"})
    update_data["transaction_date"] = update_data["transaction_date"].isoformat()

    try:
        response = supabase.table("transactions") \
            .update(update_data) \
            .eq("id", transaction_id) \
            .execute()
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Update failed: {str(e)}")


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ledger_entry(
    transaction_id: str,
    auth_data = Depends(get_current_user)
):
    """Deletes a transaction and auto-reverts the party balance."""
    token = auth_data["token"]
    user = auth_data["user"]
    supabase = get_authenticated_client(token)
    
    try:
        # We include owner_id in the filter for security
        response = supabase.table("transactions") \
            .delete() \
            .eq("id", transaction_id) \
            .eq("owner_id", user.id) \
            .execute()
            
        if not response.data:
            raise HTTPException(status_code=404, detail="Transaction not found")
        return None
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
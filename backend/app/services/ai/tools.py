# The Hands: Functions the AI calls (DB lookups, math)
# backend/app/services/ai/tools.py
from langchain_core.tools import tool
from app.services.supabase import get_party_id_by_name

@tool
def search_party_by_name(name: str, owner_id: str):
    """
    Search for a party's UUID using their name or alias. 
    Use this whenever a name is mentioned in a transaction or query.
    """
    # This will be called by the engine during execution
    return f"Searching for {name}..." 

@tool
def get_ledger_history(party_id: str, limit: int = 10):
    """Fetches the last few transactions for a specific party ID."""
    return f"Fetching history for {party_id}..."
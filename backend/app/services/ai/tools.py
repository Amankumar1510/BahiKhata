# The Hands: Functions the AI calls (DB lookups, math)
# backend/app/services/ai/tools.py
"""
These tools are called by the LangChain AI Agent during execution.
They reuse existing endpoint functions from ledger.py and utility functions from supabase.py.

IMPORTANT: The AI engine that invokes these tools must provide `auth_data` 
which is obtained from `get_current_user` dependency in the calling endpoint.
The engine passes this context when binding the tools via factory functions.
"""
from langchain_core.tools import tool
from typing import Dict, Any, List

# Import existing functions to reuse
from app.services.supabase import get_authenticated_client, get_party_id_by_name
from app.api.v1.endpoints.ledger import get_party_ledger


def create_search_party_tool(auth_data: Dict[str, Any]):
    """
    Factory function that creates a search_party_by_name tool 
    with the auth context baked in.
    """
    @tool
    async def search_party_by_name(name: str) -> Dict[str, Any]:
        """
        Search for a party's UUID using their name or alias. 
        Use this whenever a name is mentioned in a transaction or query.
        Returns the party_id and basic info if found.
        """
        token = auth_data["token"]
        user = auth_data["user"]
        supabase = get_authenticated_client(token)
        
        try:
            # Reuse existing get_party_id_by_name from supabase.py
            party_id = await get_party_id_by_name(supabase, user.id, name)
            
            # Get additional party info
            response = supabase.table("parties") \
                .select("id, name, party_type, phone, balance") \
                .eq("id", party_id) \
                .single() \
                .execute()
            
            party = response.data
            return {
                "found": True,
                "party_id": party["id"],
                "name": party["name"],
                "party_type": party.get("party_type"),
                "current_balance": party.get("balance", 0)
            }
        except Exception as e:
            return {"found": False, "error": str(e)}
    
    return search_party_by_name


def create_ledger_history_tool(auth_data: Dict[str, Any]):
    """
    Factory function that creates a get_ledger_history tool 
    with the auth context baked in.
    """
    @tool
    async def get_ledger_history(party_id: str, limit: int = 10) -> Dict[str, Any]:
        """
        Fetches the last few transactions for a specific party ID.
        Reuses the existing get_party_ledger endpoint function.
        """
        try:
            # Reuse existing get_party_ledger from ledger.py
            transactions = await get_party_ledger(party_id, auth_data)
            
            # Apply limit and format for AI consumption
            limited_txns = transactions[:limit]
            
            return {
                "party_id": party_id,
                "count": len(limited_txns),
                "transactions": [
                    {
                        "id": str(txn["id"]),
                        "transaction_type": txn["transaction_type"],
                        "amount": txn["amount"],
                        "description": txn.get("description"),
                        "transaction_date": str(txn["transaction_date"])
                    }
                    for txn in limited_txns
                ]
            }
        except Exception as e:
            return {"error": str(e), "transactions": []}
    
    return get_ledger_history


def get_ai_tools(auth_data: Dict[str, Any]) -> List:
    """
    Returns the list of tools for the AI agent, with auth context bound.
    
    This function should be called from the AI engine/endpoint where
    auth_data is available from the get_current_user dependency.
    """
    return [
        create_search_party_tool(auth_data),
        create_ledger_history_tool(auth_data),
    ]
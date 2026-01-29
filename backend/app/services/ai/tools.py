# The Hands: Functions the AI calls (DB lookups, math)
# backend/app/services/ai/tools.py
"""
These tools are called by the LangChain AI Agent during execution.
They reuse existing endpoint functions from ledger.py and utility functions from supabase.py.
"""
from langchain_core.tools import tool
from typing import Dict, Any, List
import logging

# Configure logging for AI tools debugging
logger = logging.getLogger("ai.tools")
logger.setLevel(logging.DEBUG)

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
        logger.info(f"🔍 [search_party_by_name] Called with name='{name}'")
        
        token = auth_data["token"]
        user = auth_data["user"]
        logger.debug(f"🔍 [search_party_by_name] User ID: {user.id}")
        
        supabase = get_authenticated_client(token)
        
        try:
            # Reuse existing get_party_id_by_name from supabase.py
            logger.debug(f"🔍 [search_party_by_name] Calling get_party_id_by_name...")
            party_id = await get_party_id_by_name(supabase, user.id, name)
            logger.info(f"🔍 [search_party_by_name] Found party_id: {party_id}")
            
            # Get additional party info
            logger.debug(f"🔍 [search_party_by_name] Fetching party details...")
            response = supabase.table("parties") \
                .select("id, name, party_type, phone, current_balance") \
                .eq("id", party_id) \
                .single() \
                .execute()
            
            party = response.data
            result = {
                "found": True,
                "party_id": party["id"],
                "name": party["name"],
                "party_type": party.get("party_type"),
                "current_balance": party.get("current_balance", 0)
            }
            logger.info(f"🔍 [search_party_by_name] SUCCESS: {result}")
            return result
            
        except Exception as e:
            logger.error(f"🔍 [search_party_by_name] ERROR: {str(e)}")
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
        logger.info(f"📒 [get_ledger_history] Called with party_id='{party_id}', limit={limit}")
        
        try:
            # Reuse existing get_party_ledger from ledger.py
            logger.debug(f"📒 [get_ledger_history] Calling get_party_ledger...")
            transactions = await get_party_ledger(party_id, auth_data)
            logger.info(f"📒 [get_ledger_history] Got {len(transactions)} transactions")
            
            # Apply limit and format for AI consumption
            limited_txns = transactions[:limit]
            
            result = {
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
            logger.info(f"📒 [get_ledger_history] SUCCESS: Returning {result['count']} transactions")
            return result
            
        except Exception as e:
            logger.error(f"📒 [get_ledger_history] ERROR: {str(e)}")
            return {"error": str(e), "transactions": []}
    
    return get_ledger_history


def get_ai_tools(auth_data: Dict[str, Any]) -> List:
    """
    Returns the list of tools for the AI agent, with auth context bound.
    """
    logger.info("🛠️ [get_ai_tools] Creating tools with auth context")
    tools = [
        create_search_party_tool(auth_data),
        create_ledger_history_tool(auth_data),
    ]
    logger.info(f"🛠️ [get_ai_tools] Created {len(tools)} tools: {[t.name for t in tools]}")
    return tools
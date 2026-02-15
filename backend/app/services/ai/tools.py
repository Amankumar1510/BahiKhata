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
from app.api.v1.endpoints.ledger import get_party_ledger, get_ledger_by_name, add_ledger_entry, update_ledger_entry
from app.api.v1.endpoints.parties import create_party, update_party
from app.models.party import PartyCreate
from app.models.transaction import TransactionCreate


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


def create_add_party_tool(auth_data: Dict[str, Any]):
    """
    Factory function that creates a add_party tool 
    with the auth context baked in.
    """
    @tool
    async def add_party(name: str, party_type: str, phone: str = None, aliases: List[str] = []) -> Dict[str, Any]:
        """
        Create a new party (Customer or Supplier) in the ledger.
        party_type must be either 'CUSTOMER' or 'SUPPLIER'.
        """
        logger.info(f"🆕 [add_party] Called with name='{name}', type='{party_type}'")
        
        try:
            # Validate input using Pydantic model
            party_data = {
                "name": name,
                "party_type": party_type.upper(),
                "phone": phone,
                "aliases": aliases
            }
            party = PartyCreate(**party_data)
            
            # Use existing endpoint logic
            logger.debug(f"🆕 [add_party] Calling create_party endpoint function...")
            created_party = await create_party(party, auth_data)
            
            logger.info(f"🆕 [add_party] SUCCESS: Created party {created_party['id']}")
            return {
                "success": True,
                "party": created_party,
                "message": f"Successfully created {party_type} '{name}'"
            }
                
        except Exception as e:
            logger.error(f"🆕 [add_party] ERROR: {str(e)}")
            return {
                "success": False, 
                "error": str(e),
                "message": f"Failed to create party: {str(e)}"
            }
    
    return add_party


def create_update_party_tool(auth_data: Dict[str, Any]):
    """
    Factory function that creates an update_party tool
    reusing the existing update_party endpoint.
    """
    @tool
    async def update_party_details(party_id: str, name: str, party_type: str, phone: str = None, aliases: List[str] = []) -> Dict[str, Any]:
        """
        Update an existing party's details (name, aliases, phone, etc.).
        party_id: The UUID of the party to update.
        name: The new name (required by data model).
        party_type: 'CUSTOMER' or 'SUPPLIER' (required by data model).
        """
        logger.info(f"✏️ [update_party] Called for id='{party_id}', name='{name}'")
        
        try:
            # Validate input using Pydantic model
            # Note: The API requires a full PartyCreate object even for updates
            party_content = {
                "name": name,
                "party_type": party_type.upper(),
                "phone": phone,
                "aliases": aliases
            }
            party_update = PartyCreate(**party_content)
            
            # Call existing endpoint
            logger.debug(f"✏️ [update_party] Calling update_party endpoint function...")
            updated_party = await update_party(party_id, party_update, auth_data)
            
            logger.info(f"✏️ [update_party] SUCCESS: Updated party {updated_party['id']}")
            return {
                "success": True,
                "party": updated_party,
                "message": f"Successfully updated party '{name}'"
            }
            
        except Exception as e:
            logger.error(f"✏️ [update_party] ERROR: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to update party: {str(e)}"
            }

    return update_party_details

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

def create_ledger_by_name_tool(auth_data: Dict[str, Any]):
    """
    Factory function that creates a get_ledger_by_name tool
    reusing the existing get_ledger_by_name endpoint.
    """
    @tool
    async def get_party_ledger_by_name(name: str) -> Dict[str, Any]:
        """
        Fetch the transaction history (ledger) for a party using their name.
        Use this when the user asks for history/ledger but only provides a name.
        """
        logger.info(f"📒 [get_party_ledger_by_name] Called with name='{name}'")
        
        try:
            # Reuse existing endpoint logic
            logger.debug(f"📒 [get_party_ledger_by_name] Calling get_ledger_by_name endpoint function...")
            transactions = await get_ledger_by_name(name, auth_data)
            
            # Format for AI
            result = {
                "party_name": name,
                "count": len(transactions),
                "transactions": [
                    {
                        "id": str(txn["id"]),
                        "transaction_type": txn["transaction_type"],
                        "amount": txn["amount"],
                        "description": txn.get("description"),
                        "transaction_date": str(txn["transaction_date"])
                    }
                    for txn in transactions[:10] # Limit to 10 for AI context window
                ]
            }
            logger.info(f"📒 [get_party_ledger_by_name] SUCCESS: Returning {result['count']} transactions")
            return result
            
        except Exception as e:
            logger.error(f"📒 [get_party_ledger_by_name] ERROR: {str(e)}")
            return {"error": str(e), "message": f"Failed to fetch ledger for '{name}': {str(e)}"}

    return get_party_ledger_by_name


def create_add_transaction_tool(auth_data: Dict[str, Any]):
    """
    Factory function that creates an add_transaction tool
    reusing the existing add_ledger_entry endpoint.
    """
    @tool
    async def add_transaction(
        party_name: str, 
        transaction_type: str, 
        amount: float = 0.0, 
        description: str = None, 
        quantity: float = 0.0, 
        rate: float = 0.0
    ) -> Dict[str, Any]:
        """
        Record a new transaction (GIVE or GOT) for a party.
        party_name: Name of the party.
        transaction_type: 'GIVE' (You gave/sold) or 'GOT' (You received/bought).
        amount: Total value of transaction (if quantity/rate unknown).
        quantity: Amount of goods (default 0).
        rate: Price per unit (default 0).
        """
        logger.info(f"💸 [add_transaction] Called: {transaction_type} {amount} for {party_name}")
        
        try:
            # Smart logic to handle amount vs rate/qty
            final_qty = quantity
            final_rate = rate
            
            # If standard amount is given but no specific rate/qty, treat as 1 unit * amount
            if amount > 0 and final_rate == 0 and final_qty == 0:
                final_qty = 1.0
                final_rate = amount
            
            from datetime import datetime
            
            # Validate input using Pydantic model
            txn_data = {
                "party_name": party_name,
                "transaction_type": transaction_type.upper(),
                "quantity": final_qty,
                "rate_per_unit": final_rate,
                "description": description,
                "transaction_date": datetime.now(),
                "unit": "kg" # Defaulting for now
            }
            txn = TransactionCreate(**txn_data)
            
            # Reuse existing endpoint logic
            logger.debug(f"💸 [add_transaction] Calling add_ledger_entry endpoint function...")
            created_txn = await add_ledger_entry(txn, auth_data)
            
            logger.info(f"💸 [add_transaction] SUCCESS: Created txn {created_txn['id']}")
            return {
                "success": True,
                "transaction": created_txn,
                "message": f"Successfully recorded {transaction_type} of {created_txn['amount']} for {party_name}"
            }
            
        except Exception as e:
            logger.error(f"💸 [add_transaction] ERROR: {str(e)}")
            return {
                "success": False, 
                "error": str(e),
                "message": f"Failed to add transaction: {str(e)}"
            }

    return add_transaction


def create_update_transaction_tool(auth_data: Dict[str, Any]):
    """
    Factory function that creates an update_transaction tool
    reusing the existing update_ledger_entry endpoint.
    """
    @tool
    async def update_transaction(
        transaction_id: str,
        transaction_type: str = None, 
        amount: float = None, 
        description: str = None, 
        quantity: float = None, 
        rate: float = None,
        party_id: str = None # Usually we don't change party, but model requires it if we rebuild
    ) -> Dict[str, Any]:
        """
        Update an existing transaction.
        Only provide the fields you want to change.
        """
        logger.info(f"✏️ [update_transaction] Called for id='{transaction_id}'")
        
        token = auth_data["token"]
        # We need to fetch the existing transaction first to ensure we have all required fields for TransactionCreate
        supabase = get_authenticated_client(token)
        
        try:
            # 1. Fetch existing
            existing_resp = supabase.table("transactions").select("*").eq("id", transaction_id).single().execute()
            if not existing_resp.data:
                return {"success": False, "error": "Transaction not found"}
            
            existing = existing_resp.data
            
            # 2. Merge updates
            # If AI didn't provide a value, keep existing
            final_type = transaction_type.upper() if transaction_type else existing["transaction_type"]
            final_qty = quantity if quantity is not None else existing["quantity"]
            final_rate = rate if rate is not None else existing["rate_per_unit"]
            final_desc = description if description is not None else existing["description"]
            final_party_id = party_id if party_id else existing["party_id"]
            
            # If amount changed but rate/qty didn't, we might need to adjust logic
            # For now, let's assume if amount is passed, we update rate/qty accordingly if possible, 
            # OR honestly just let the model validation handle it.
            # But wait, the DB stores qty and rate. Amount is calculated? 
            # The TransactionResponse calculate amount. The DB might not store it or it might be a generated column.
            # Looking at TransactionCreate, it has qty and rate.
            
            if amount is not None:
                # If only amount is updated, we default qty=1, rate=amount to be safe, 
                # OR we try to preserve qty and update rate.
                if final_qty > 0:
                    final_rate = amount / final_qty
                else:
                    final_qty = 1.0
                    final_rate = amount
            
            from datetime import datetime
            
            # 3. Construct TransactionCreate
            # We must parse the string date from DB back to datetime object
            # DB format is usually ISO
            txn_date = datetime.fromisoformat(existing["transaction_date"])
            
            txn_data = {
                "party_id": final_party_id,
                "transaction_type": final_type,
                "quantity": final_qty,
                "rate_per_unit": final_rate,
                "description": final_desc,
                "transaction_date": txn_date, # Keep original date unless we want to allow updating it too
                "unit": existing["unit"],
                "payment_mode": existing["payment_mode"]
            }
            
            txn_update = TransactionCreate(**txn_data)
            
            # 4. Call endpoint
            logger.debug(f"✏️ [update_transaction] Calling update_ledger_entry endpoint function...")
            updated_txn = await update_ledger_entry(transaction_id, txn_update, auth_data)
            
            logger.info(f"✏️ [update_transaction] SUCCESS: Updated txn {updated_txn['id']}")
            return {
                "success": True,
                "transaction": updated_txn,
                "message": f"Successfully updated transaction {transaction_id}"
            }
            
        except Exception as e:
            logger.error(f"✏️ [update_transaction] ERROR: {str(e)}")
            return {
                "success": False, 
                "error": str(e),
                "message": f"Failed to update transaction: {str(e)}"
            }

    return update_transaction


def get_ai_tools(auth_data: Dict[str, Any]) -> List:
    """
    Returns the list of tools for the AI agent, with auth context bound.
    """
    logger.info("🛠️ [get_ai_tools] Creating tools with auth context")
    tools = [
        create_search_party_tool(auth_data),
        create_ledger_history_tool(auth_data),
        create_add_party_tool(auth_data),
        create_update_party_tool(auth_data),
        create_ledger_by_name_tool(auth_data),
        create_add_transaction_tool(auth_data),
        create_update_transaction_tool(auth_data),
    ]
    logger.info(f"🛠️ [get_ai_tools] Created {len(tools)} tools: {[t.name for t in tools]}")
    return tools
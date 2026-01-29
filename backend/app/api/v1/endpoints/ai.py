# backend/app/api/v1/endpoints/ai.py
from fastapi import APIRouter, Depends, HTTPException, Body
from app.core.security import get_current_user
from app.services.ai.engine import LedgerEngine

router = APIRouter()
# Initialize the engine once (Singleton pattern is better for production)
ai_engine = LedgerEngine()

@router.post("/command")
async def process_ai_command(
    text: str = Body(..., embed=True),
    auth_data = Depends(get_current_user)
):
    """
    Primary endpoint for written/text commands.
    Injects owner_id and token into the LangGraph state.
    """
    user = auth_data["user"]
    token = auth_data["token"]
    
    try:
        # Run the LangGraph workflow
        response = await ai_engine.run_command(
            text=text, 
            auth_data=auth_data
        )
        
        return {
            "status": "success",
            "response": response
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"AI Engine Error: {str(e)}"
        )
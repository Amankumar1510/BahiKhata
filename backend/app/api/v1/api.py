from fastapi import APIRouter
from app.api.v1.endpoints import auth, parties, ledger, ai

api_router = APIRouter()

# Include auth routes
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(parties.router, prefix="/parties", tags=["Parties"])
api_router.include_router(ledger.router, prefix="/ledger", tags=["Ledger"])
api_router.include_router(ai.router, prefix="/ai", tags=["AI Operations"])

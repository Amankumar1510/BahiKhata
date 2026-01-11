# backend/app/models/party.py
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class PartyBase(BaseModel):
    name: str = Field(..., example="Akku")
    aliases: List[str] = Field(default=[], example=["Nabbu", "kurbaan"])
    phone: Optional[str] = None
    party_type: str = Field(..., pattern="^(CUSTOMER|SUPPLIER)$")

class PartyCreate(PartyBase):
    pass

class PartyResponse(PartyBase):
    id: str
    owner_id: str
    current_balance: float = 0.0  # Default to 0 if not set in database
    created_at: datetime

    class Config:
        from_attributes = True
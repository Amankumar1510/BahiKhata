from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class TransactionBase(BaseModel):
    party_id: str
    quantity: float = Field(default=0.0, description="Weight or count")
    rate_per_unit: float = Field(default=0.0, description="Price per unit")
    unit: str = "kg"
    transaction_type: str = Field(..., pattern="^(GIVE|GOT)$")
    payment_mode: str = "NONE" # CASH, UPI, NEFT, CHEQUE
    reference_id: Optional[str] = None
    description: Optional[str] = None
    transaction_date: datetime # The date the transaction actually happened

class TransactionCreate(TransactionBase):
    party_id: Optional[str] = None
    party_name: Optional[str] = None # Added for convenience

class TransactionResponse(TransactionBase):
    id: str
    owner_id: str
    amount: float # This is the auto-calculated (qty * rate) from DB
    created_at: datetime

    class Config:
        from_attributes = True
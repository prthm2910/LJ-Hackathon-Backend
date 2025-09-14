from pydantic import BaseModel, Field
from typing import Optional
from datetime import date

# ==================================================
# Pydantic Models for API Data Validation
# ==================================================

class QueryRequest(BaseModel):
    """Model for the AI chat request body."""
    question: str
    user_id: str


class PermissionsUpdateRequest(BaseModel):
    """Model for updating a user's data access permissions."""
    perm_assets: bool
    perm_liabilities: bool
    perm_transactions: bool
    perm_investments: bool
    perm_credit_score: bool
    perm_epf_balance: bool


class TransactionCreate(BaseModel):
    """Model for creating a new transaction."""
    date: date
    description: str
    category: str
    amount: float
    type: str


class AssetCreate(BaseModel):
    """Model for creating a new asset."""
    name: str
    type: str
    value: float


class LiabilityCreate(BaseModel):
    """Model for creating a new liability."""
    name: str
    type: str
    # Use an alias to allow the frontend to send camelCase (outstandingBalance)
    outstanding_balance: float = Field(..., alias='outstandingBalance')


class InvestmentCreate(BaseModel):
    """Model for creating a new investment."""
    name: str
    ticker: Optional[str] = None
    type: str
    quantity: Optional[float] = None
    # Use an alias to allow the frontend to send camelCase (currentValue)
    current_value: float = Field(..., alias='currentValue')


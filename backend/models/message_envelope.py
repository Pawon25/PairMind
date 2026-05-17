from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

class MsgType(str, Enum):
    PROPOSE = "PROPOSE"
    COUNTER = "COUNTER"
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    WALK_AWAY = "WALK_AWAY"

class DealTerms(BaseModel):
    unit_price: float
    quantity: int
    delivery_date: str        # "2026-08-30"
    payment_terms: str        # "Net-60"
    warranty_years: int

class Citation(BaseModel):
    source: str               # filename or URL
    section: Optional[str] = None
    retrieved_date: Optional[str] = None  # for web citations

class MessageEnvelope(BaseModel):
    agent_id: str
    msg_type: MsgType
    payload: DealTerms
    rationale: str
    citations: List[Citation]
    turn: int
from typing import TypedDict, List, Optional
from .message_envelope import MessageEnvelope, DealTerms

class NegotiationState(TypedDict):
    session_id: str
    messages: List[MessageEnvelope]       # full conversation history
    current_terms: Optional[DealTerms]    # last proposed terms
    turn_count: int
    outcome: Optional[str]                # AGREEMENT / WALK_AWAY / DEADLOCK / TIMEOUT
    last_terms_history: List[DealTerms]   # last 3 terms for deadlock detection
from typing import TypedDict, List, Optional
from .message_envelope import MessageEnvelope, DealTerms


class NegotiationState(TypedDict):
    session_id: str
    messages: List[MessageEnvelope]        # full conversation history (shared)
    current_terms: Optional[DealTerms]     # last proposed structured terms
    turn_count: int
    outcome: Optional[str]                 # AGREEMENT | WALK_AWAY | DEADLOCK | TIMEOUT
    last_terms_history: List[DealTerms]    # last 3 DealTerms snapshots for deadlock detection
    citation_retry: bool                   # flag: agent must revise its last message
    citation_retry_count: int              # number of retries attempted this turn
    citation_error: Optional[str]          # reason for last citation failure
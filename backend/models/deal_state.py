from typing import TypedDict, List, Optional
from .message_envelope import MessageEnvelope, DealTerms


class NegotiationState(TypedDict):
    session_id: str
    messages: List[MessageEnvelope]
    current_terms: Optional[DealTerms]
    turn_count: int
    outcome: Optional[str]
    last_terms_history: List[DealTerms]
    citation_retry: bool
    citation_retry_count: int
    citation_error: Optional[str]
    uploaded_files: List[dict]  # [{"filename": "...", "tag": "..."}]
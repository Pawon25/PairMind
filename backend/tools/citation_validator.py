from models.message_envelope import MessageEnvelope, Citation
from models.deal_state import NegotiationState
from ingestion.opensearch_store import get_client, INDEX_NAME


def _chunk_exists(source: str, section: str | None) -> bool:
    """Check if a cited document chunk actually exists in OpenSearch."""
    client = get_client()
    query: dict = {
        "query": {
            "bool": {
                "must": [{"match": {"filename": source}}]
            }
        }
    }
    if section:
        query["query"]["bool"]["must"].append({"match": {"section": section}})

    try:
        res = client.count(index=INDEX_NAME, body=query)
        return res["count"] > 0
    except Exception:
        return False  # don't block negotiation on OpenSearch errors


def _validate_citations(envelope: MessageEnvelope) -> tuple[bool, str]:
    """
    Returns (is_valid, reason).
    - No citations at all → invalid
    - URL citation missing date → invalid
    - Doc citation not found in OpenSearch → flagged but not blocked (marked UNCITED)
    """
    if not envelope.citations:
        return False, "No citations provided"

    for citation in envelope.citations:
        is_url = citation.source.startswith("http")
        if is_url:
            if not citation.retrieved_date:
                return False, f"Web citation missing retrieved_date: {citation.source}"
        else:
            # Document citation — verify chunk exists
            if not _chunk_exists(citation.source, citation.section):
                # Soft failure: flag as unverified rather than block
                citation.section = f"⚠ UNCITED: {citation.section or 'unknown section'}"

    return True, "ok"


def run_citation_validator(state: NegotiationState) -> NegotiationState:
    """
    Validates the most recent message's citations.
    - If invalid, sets a retry flag in state.
    - After 2 failures, marks message with ⚠ and lets negotiation continue.
    """
    if not state["messages"]:
        return state

    last_msg = state["messages"][-1]
    is_valid, reason = _validate_citations(last_msg)

    if is_valid:
        return {**state, "citation_retry": False, "citation_error": None}

    # Check if this is already a retry
    retry_count = state.get("citation_retry_count", 0)
    if retry_count >= 1:
        # Second failure — mark as UNCITED and continue
        last_msg.rationale = f"⚠ UNCITED WARNING: {reason}. " + last_msg.rationale
        return {**state, "citation_retry": False, "citation_retry_count": 0, "citation_error": None}

    # First failure — request retry
    return {
        **state,
        "citation_retry": True,
        "citation_retry_count": retry_count + 1,
        "citation_error": reason,
    }
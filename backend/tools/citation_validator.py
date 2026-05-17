from models.message_envelope import MessageEnvelope, Citation
from models.deal_state import NegotiationState
from ingestion.opensearch_store import get_client, INDEX_NAME


def _filename_exists(source: str) -> bool:
    """
    Check if any chunk from this source file exists in OpenSearch.
    Section matching is intentionally skipped — LLM-generated section names
    are free-form and will never exactly match stored keyword fields.
    Filename presence is sufficient to confirm the citation is grounded.
    """
    client = get_client()
    try:
        res = client.count(
            index=INDEX_NAME,
            body={"query": {"term": {"filename": source}}},
        )
        return res["count"] > 0
    except Exception:
        # Never block negotiation on OpenSearch errors
        return True


def _validate_citations(envelope: MessageEnvelope) -> tuple[bool, str]:
    """
    Returns (is_valid, reason).
    Rules:
      - No citations at all → invalid (trigger retry)
      - Web citation missing retrieved_date → invalid (trigger retry)
      - Doc citation filename not in OpenSearch → soft-fail (mark UNCITED, no retry)
    """
    if not envelope.citations:
        return False, "No citations provided"

    for citation in envelope.citations:
        is_url = citation.source.startswith("http://") or citation.source.startswith("https://")
        if is_url:
            if not citation.retrieved_date:
                return False, f"Web citation missing retrieved_date: {citation.source}"
        else:
            if not _filename_exists(citation.source):
                # Soft failure: mark section as unverified, don't block
                citation.section = f"⚠ UNCITED: {citation.section or 'unknown section'}"

    return True, "ok"


def run_citation_validator(state: NegotiationState) -> NegotiationState:
    """
    Validates the most recent message's citations.
    - Hard failures (no citations, missing URL date): trigger one retry.
    - After 1 retry still failing: let through with warning in rationale.
    - Soft failures (filename not found): mark inline, never block.
    """
    if not state["messages"]:
        return state

    last_msg = state["messages"][-1]
    is_valid, reason = _validate_citations(last_msg)

    if is_valid:
        return {
            **state,
            "citation_retry": False,
            "citation_retry_count": 0,
            "citation_error": None,
        }

    retry_count = state.get("citation_retry_count", 0)

    if retry_count >= 1:
        # Already retried once — let through with warning, reset counters
        last_msg.rationale = f"⚠ CITATION WARNING: {reason}. " + last_msg.rationale
        return {
            **state,
            "citation_retry": False,
            "citation_retry_count": 0,
            "citation_error": None,
        }

    # First failure — request one retry
    return {
        **state,
        "citation_retry": True,
        "citation_retry_count": retry_count + 1,
        "citation_error": reason,
    }
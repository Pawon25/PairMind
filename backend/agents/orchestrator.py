import time
import uuid
from typing import Literal

from langgraph.graph import StateGraph, END

from models.deal_state import NegotiationState
from models.message_envelope import MsgType, DealTerms
from agents.buyer_agent import run_buyer_node
from agents.seller_agent import run_seller_node
from tools.citation_validator import run_citation_validator

HARD_CAP = 15


# ── Termination Check ─────────────────────────────────────────────────────────

def check_termination(state: NegotiationState) -> Literal["buyer", "end"]:
    """Conditional edge after seller node. Decides: loop back to buyer or end."""

    # 1. Explicit outcome already set (WALK_AWAY from either agent)
    if state.get("outcome"):
        return "end"

    # 2. Hard turn cap
    if state["turn_count"] >= HARD_CAP:
        return "end"

    # 3. Agreement — last two messages are ACCEPT on identical terms
    msgs = state["messages"]
    if len(msgs) >= 2:
        last_two = msgs[-2:]
        if (
            all(m.msg_type == MsgType.ACCEPT for m in last_two)
            and last_two[0].payload == last_two[1].payload
        ):
            return "end"

    # 4. Deadlock — DealTerms unchanged for last 3 consecutive turns
    history = state.get("last_terms_history", [])
    if len(history) >= 3:
        if history[-1] == history[-2] == history[-3]:
            return "end"

    return "buyer"


# ── Summary Builder ───────────────────────────────────────────────────────────

def build_summary(state: NegotiationState, duration_seconds: float) -> dict:
    msgs = state["messages"]

    # Determine outcome
    outcome = state.get("outcome")
    if not outcome:
        if len(msgs) >= 2 and all(m.msg_type == MsgType.ACCEPT for m in msgs[-2:]):
            outcome = "AGREEMENT"
        else:
            history = state.get("last_terms_history", [])
            if len(history) >= 3 and history[-1] == history[-2] == history[-3]:
                outcome = "DEADLOCK"
            elif state["turn_count"] >= HARD_CAP:
                outcome = "TIMEOUT"
            else:
                outcome = "TIMEOUT"

    # Real token counting from message envelopes
    total_input_tokens  = sum(m.input_tokens  for m in msgs)
    total_output_tokens = sum(m.output_tokens for m in msgs)
    total_tokens        = total_input_tokens + total_output_tokens

    per_agent_tokens = {}
    per_agent_citations = {}
    for m in msgs:
        aid = m.agent_id
        per_agent_tokens[aid]     = per_agent_tokens.get(aid, 0) + m.input_tokens + m.output_tokens
        per_agent_citations[aid]  = per_agent_citations.get(aid, 0) + len(m.citations)

    return {
        "outcome":              outcome,
        "final_terms":          state["current_terms"].model_dump() if state["current_terms"] else None,
        "turn_count":           state["turn_count"],
        "total_tokens":         total_tokens,
        "total_input_tokens":   total_input_tokens,
        "total_output_tokens":  total_output_tokens,
        "per_agent_tokens":     per_agent_tokens,
        "per_agent_citations":  per_agent_citations,
        "duration_seconds":     round(duration_seconds, 2),
    }


# ── Retry-aware agent wrappers ────────────────────────────────────────────────

def buyer_with_retry(state: NegotiationState) -> NegotiationState:
    """Run buyer → validate citations → retry once if needed."""
    state = run_buyer_node(state)
    state = run_citation_validator(state)

    if state.get("citation_retry"):
        state = run_buyer_node(state)
        state = run_citation_validator(state)

    # Always clear retry flags after this node completes
    return {**state, "citation_retry": False, "citation_retry_count": 0}


def seller_with_retry(state: NegotiationState) -> NegotiationState:
    """Run seller → validate citations → retry once if needed."""
    state = run_seller_node(state)
    state = run_citation_validator(state)

    if state.get("citation_retry"):
        state = run_seller_node(state)
        state = run_citation_validator(state)

    return {**state, "citation_retry": False, "citation_retry_count": 0}


# ── Graph Definition ──────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    graph = StateGraph(NegotiationState)

    graph.add_node("buyer",  buyer_with_retry)
    graph.add_node("seller", seller_with_retry)

    graph.set_entry_point("buyer")
    graph.add_edge("buyer", "seller")
    graph.add_conditional_edges(
        "seller",
        check_termination,
        {"buyer": "buyer", "end": END},
    )

    return graph.compile()


# ── Standalone runner (for testing) ──────────────────────────────────────────

def run_negotiation(session_id: str | None = None) -> dict:
    session_id = session_id or str(uuid.uuid4())

    initial_state: NegotiationState = {
        "session_id":           session_id,
        "messages":             [],
        "current_terms":        None,
        "turn_count":           0,
        "outcome":              None,
        "last_terms_history":   [],
        "citation_retry":       False,
        "citation_retry_count": 0,
        "citation_error":       None,
    }

    graph = build_graph()
    start = time.time()
    final_state = graph.invoke(initial_state)
    duration = time.time() - start

    summary = build_summary(final_state, duration)
    summary["session_id"] = session_id
    return summary
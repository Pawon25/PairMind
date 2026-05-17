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
    """Conditional edge after seller+validator. Decides: loop or end."""

    # 1. Explicit outcome already set (WALK_AWAY from either agent)
    if state.get("outcome"):
        return "end"

    # 2. Hard turn cap
    if state["turn_count"] >= HARD_CAP:
        return "end"

    # 3. Agreement — both last two messages are ACCEPT on identical terms
    msgs = state["messages"]
    if len(msgs) >= 2:
        last_two = msgs[-2:]
        if (
            all(m.msg_type == MsgType.ACCEPT for m in last_two)
            and last_two[0].payload == last_two[1].payload
        ):
            return "end"

    # 4. Deadlock — DealTerms unchanged for last 3 turns
    history = state.get("last_terms_history", [])
    if len(history) >= 3:
        if history[-1] == history[-2] == history[-3]:
            return "end"

    return "buyer"


# ── Summary Emitter ───────────────────────────────────────────────────────────

def _terms_equal(a: DealTerms, b: DealTerms) -> bool:
    return a.model_dump() == b.model_dump()


def build_summary(state: NegotiationState, duration_seconds: float) -> dict:
    msgs = state["messages"]

    # Determine outcome
    outcome = state.get("outcome")
    if not outcome:
        if state["turn_count"] >= HARD_CAP:
            outcome = "TIMEOUT"
        elif len(msgs) >= 2 and all(m.msg_type == MsgType.ACCEPT for m in msgs[-2:]):
            outcome = "AGREEMENT"
        else:
            history = state.get("last_terms_history", [])
            if len(history) >= 3 and history[-1] == history[-2] == history[-3]:
                outcome = "DEADLOCK"
            else:
                outcome = "TIMEOUT"

    total_tokens = 0  # token counting handled externally via LangSmith or logs
    per_agent_citations = {"buyer": 0, "seller": 0}
    for m in msgs:
        per_agent_citations[m.agent_id] = per_agent_citations.get(m.agent_id, 0) + len(m.citations)

    return {
        "outcome": outcome,
        "final_terms": state["current_terms"].model_dump() if state["current_terms"] else None,
        "turn_count": state["turn_count"],
        "total_tokens": total_tokens,
        "duration_seconds": round(duration_seconds, 2),
        "per_agent_citations": per_agent_citations,
    }


# ── Retry-aware agent wrappers ────────────────────────────────────────────────

def buyer_with_retry(state: NegotiationState) -> NegotiationState:
    """Run buyer, then validator. If validator requests retry, re-run buyer once."""
    state = run_buyer_node(state)
    state = run_citation_validator(state)

    if state.get("citation_retry"):
        # Inject error hint into last user message context via state flag
        state = run_buyer_node(state)
        state = run_citation_validator(state)

    state["citation_retry"] = False
    state["citation_retry_count"] = 0
    return state


def seller_with_retry(state: NegotiationState) -> NegotiationState:
    """Run seller, then validator. If validator requests retry, re-run seller once."""
    state = run_seller_node(state)
    state = run_citation_validator(state)

    if state.get("citation_retry"):
        state = run_seller_node(state)
        state = run_citation_validator(state)

    state["citation_retry"] = False
    state["citation_retry_count"] = 0
    return state


# ── Graph Definition ──────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    graph = StateGraph(NegotiationState)

    graph.add_node("buyer", buyer_with_retry)
    graph.add_node("seller", seller_with_retry)

    graph.set_entry_point("buyer")

    # buyer → seller (always)
    graph.add_edge("buyer", "seller")

    # seller → termination check → loop or end
    graph.add_conditional_edges(
        "seller",
        check_termination,
        {"buyer": "buyer", "end": END},
    )

    return graph.compile()


# ── Public runner ─────────────────────────────────────────────────────────────

def run_negotiation(session_id: str | None = None) -> dict:
    """Run a full negotiation and return the summary."""
    session_id = session_id or str(uuid.uuid4())

    initial_state: NegotiationState = {
        "session_id": session_id,
        "messages": [],
        "current_terms": None,
        "turn_count": 0,
        "outcome": None,
        "last_terms_history": [],
        "citation_retry": False,
        "citation_retry_count": 0,
        "citation_error": None,
    }

    graph = build_graph()
    start = time.time()
    final_state = graph.invoke(initial_state)
    duration = time.time() - start

    summary = build_summary(final_state, duration)
    summary["session_id"] = session_id
    return summary
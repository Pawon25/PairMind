import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from models.message_envelope import MessageEnvelope, MsgType, DealTerms, Citation
from models.deal_state import NegotiationState
from agents.buyer_agent import run_buyer_node
from agents.seller_agent import run_seller_node
from tools.citation_validator import run_citation_validator

# ── helpers ──────────────────────────────────────────────────────────────────

def blank_state(session_id="test-p2") -> NegotiationState:
    return {
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

# ── tests ─────────────────────────────────────────────────────────────────────

def test_buyer_opens():
    print("\n1. Buyer opening proposal...")
    state = blank_state()
    state = run_buyer_node(state)

    msg = state["messages"][-1]
    assert msg.agent_id == "buyer", "agent_id must be buyer"
    assert msg.msg_type == MsgType.PROPOSE, "first move must be PROPOSE"
    assert msg.payload.unit_price <= 580, f"Buyer opened above ceiling: {msg.payload.unit_price}"
    assert len(msg.citations) > 0, "Buyer must include citations"
    print(f"   ✓ Buyer proposed ${msg.payload.unit_price}/unit | citations: {len(msg.citations)}")


def test_seller_responds():
    print("\n2. Seller responding to buyer proposal...")
    state = blank_state()
    state = run_buyer_node(state)   # buyer opens
    state = run_seller_node(state)  # seller responds

    msg = state["messages"][-1]
    assert msg.agent_id == "seller", "agent_id must be seller"
    assert msg.msg_type in {MsgType.COUNTER, MsgType.ACCEPT, MsgType.REJECT, MsgType.WALK_AWAY}
    assert msg.payload.unit_price >= 501, f"Seller went below floor: {msg.payload.unit_price}"
    assert len(msg.citations) > 0, "Seller must include citations"
    print(f"   ✓ Seller replied {msg.msg_type} at ${msg.payload.unit_price}/unit | citations: {len(msg.citations)}")


def test_citation_validator_passes_valid():
    print("\n3. Citation validator — valid message...")
    state = blank_state()
    state = run_buyer_node(state)
    state = run_citation_validator(state)

    assert state.get("citation_retry") == False, "Valid message should not trigger retry"
    print("   ✓ Validator passed valid message")


def test_citation_validator_catches_empty():
    print("\n4. Citation validator — no citations...")
    state = blank_state()

    # Inject a message with no citations
    fake = MessageEnvelope(
        agent_id="buyer",
        msg_type=MsgType.PROPOSE,
        payload=DealTerms(unit_price=545.0, quantity=600, delivery_date="2026-08-30", payment_terms="Net-60", warranty_years=2),
        rationale="Market price is $545 per unit.",
        citations=[],
        turn=1,
    )
    state["messages"] = [fake]
    state["turn_count"] = 1

    state = run_citation_validator(state)
    assert state.get("citation_retry") == True, "Missing citations should trigger retry"
    print("   ✓ Validator caught missing citations and requested retry")


def test_seller_floor_not_breached():
    print("\n5. Seller floor price protection (2-turn exchange)...")
    state = blank_state()
    state = run_buyer_node(state)
    state = run_seller_node(state)

    seller_msg = state["messages"][-1]
    assert seller_msg.payload.unit_price >= 501, f"Floor breached: {seller_msg.payload.unit_price}"
    print(f"   ✓ Seller held floor: ${seller_msg.payload.unit_price}/unit ≥ $501")


def test_turn_count_increments():
    print("\n6. Turn count increments correctly...")
    state = blank_state()
    state = run_buyer_node(state)
    assert state["turn_count"] == 1
    state = run_seller_node(state)
    assert state["turn_count"] == 2
    print("   ✓ Turn count: 2 after buyer + seller")


# ── runner ────────────────────────────────────────────────────────────────────

def run():
    tests = [
        test_buyer_opens,
        test_seller_responds,
        test_citation_validator_passes_valid,
        test_citation_validator_catches_empty,
        test_seller_floor_not_breached,
        test_turn_count_increments,
    ]

    passed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"   ✗ FAILED: {e}")

    print(f"\n{'✅' if passed == len(tests) else '⚠'} Phase 2: {passed}/{len(tests)} tests passed")

if __name__ == "__main__":
    run()
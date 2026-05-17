import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from models.message_envelope import MessageEnvelope, MsgType, DealTerms, Citation
from models.deal_state import NegotiationState
from agents.orchestrator import check_termination, build_summary, run_negotiation


# ── helpers ───────────────────────────────────────────────────────────────────

def make_terms(price: float) -> DealTerms:
    return DealTerms(unit_price=price, quantity=600, delivery_date="2026-08-30",
                     payment_terms="Net-60", warranty_years=2)

def make_msg(agent: str, msg_type: MsgType, price: float, turn: int) -> MessageEnvelope:
    return MessageEnvelope(
        agent_id=agent, msg_type=msg_type, payload=make_terms(price),
        rationale="test", citations=[Citation(source="test.md", section="S1")], turn=turn
    )

def blank_state(**overrides) -> NegotiationState:
    base: NegotiationState = {
        "session_id": "test-p3",
        "messages": [],
        "current_terms": None,
        "turn_count": 0,
        "outcome": None,
        "last_terms_history": [],
        "citation_retry": False,
        "citation_retry_count": 0,
        "citation_error": None,
    }
    return {**base, **overrides}


# ── tests ─────────────────────────────────────────────────────────────────────

def test_agreement_detection():
    print("\n1. Termination: both ACCEPT on same terms → end...")
    msgs = [
        make_msg("buyer", MsgType.ACCEPT, 545.0, 3),
        make_msg("seller", MsgType.ACCEPT, 545.0, 4),
    ]
    state = blank_state(messages=msgs, turn_count=4,
                        last_terms_history=[make_terms(545.0)] * 2)
    result = check_termination(state)
    assert result == "end", f"Expected end, got {result}"
    print("   ✓ Agreement detected → end")


def test_walk_away_detection():
    print("\n2. Termination: WALK_AWAY outcome set → end...")
    state = blank_state(outcome="WALK_AWAY", turn_count=3)
    result = check_termination(state)
    assert result == "end", f"Expected end, got {result}"
    print("   ✓ Walk-away detected → end")


def test_hard_cap():
    print("\n3. Termination: turn_count >= 15 → end...")
    state = blank_state(turn_count=15)
    result = check_termination(state)
    assert result == "end", f"Expected end, got {result}"
    print("   ✓ Hard cap (15 turns) → end")


def test_deadlock_detection():
    print("\n4. Termination: same terms for 3 turns → end...")
    terms = [make_terms(545.0)] * 3
    state = blank_state(turn_count=6, last_terms_history=terms)
    result = check_termination(state)
    assert result == "end", f"Expected end, got {result}"
    print("   ✓ Deadlock (3 identical turns) → end")


def test_continues_when_progressing():
    print("\n5. Termination: different terms, turn 4 → continue...")
    terms = [make_terms(580.0), make_terms(560.0), make_terms(545.0)]
    msgs = [make_msg("buyer", MsgType.COUNTER, 545.0, 4)]
    state = blank_state(messages=msgs, turn_count=4, last_terms_history=terms)
    result = check_termination(state)
    assert result == "buyer", f"Expected buyer, got {result}"
    print("   ✓ Negotiation continues → buyer")


def test_summary_agreement():
    print("\n6. Summary: AGREEMENT outcome...")
    msgs = [
        make_msg("buyer", MsgType.ACCEPT, 545.0, 3),
        make_msg("seller", MsgType.ACCEPT, 545.0, 4),
    ]
    state = blank_state(messages=msgs, turn_count=4,
                        current_terms=make_terms(545.0),
                        last_terms_history=[make_terms(545.0)] * 2)
    summary = build_summary(state, duration_seconds=12.5)
    assert summary["outcome"] == "AGREEMENT"
    assert summary["final_terms"]["unit_price"] == 545.0
    assert summary["turn_count"] == 4
    print(f"   ✓ Summary: {summary['outcome']} at ${summary['final_terms']['unit_price']}/unit")


def test_full_negotiation():
    print("\n7. Full negotiation run (uses Claude API — may take ~30s)...")
    summary = run_negotiation(session_id="test-full-p3")
    assert summary["outcome"] in {"AGREEMENT", "WALK_AWAY", "DEADLOCK", "TIMEOUT"}
    assert summary["turn_count"] > 0
    assert summary["turn_count"] <= 15
    assert summary["duration_seconds"] > 0
    print(f"   ✓ Outcome: {summary['outcome']} | Turns: {summary['turn_count']} | Duration: {summary['duration_seconds']}s")
    if summary["final_terms"]:
        print(f"   ✓ Final price: ${summary['final_terms']['unit_price']}/unit")


# ── runner ────────────────────────────────────────────────────────────────────

def run():
    tests = [
        test_agreement_detection,
        test_walk_away_detection,
        test_hard_cap,
        test_deadlock_detection,
        test_continues_when_progressing,
        test_summary_agreement,
        test_full_negotiation,   # API call — runs last
    ]

    passed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"   ✗ FAILED: {e}")

    print(f"\n{'✅' if passed == len(tests) else '⚠'} Phase 3: {passed}/{len(tests)} tests passed")

if __name__ == "__main__":
    run()
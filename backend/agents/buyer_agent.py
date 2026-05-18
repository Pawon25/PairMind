import os
import json
from anthropic import Anthropic
from models.message_envelope import MessageEnvelope, MsgType, DealTerms, Citation
from models.deal_state import NegotiationState
from retrieval.hybrid_retriever import buyer_retrieve
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Valid state transitions: what msg_types are allowed given the last message
_VALID_TRANSITIONS: dict[MsgType | None, list[MsgType]] = {
    None:               [MsgType.PROPOSE],
    MsgType.PROPOSE:    [MsgType.COUNTER, MsgType.ACCEPT, MsgType.REJECT, MsgType.WALK_AWAY],
    MsgType.COUNTER:    [MsgType.COUNTER, MsgType.ACCEPT, MsgType.REJECT, MsgType.WALK_AWAY],
    MsgType.ACCEPT:     [MsgType.ACCEPT, MsgType.WALK_AWAY],
    MsgType.REJECT:     [MsgType.PROPOSE, MsgType.COUNTER, MsgType.WALK_AWAY],
    MsgType.WALK_AWAY:  [],
}

BUYER_SYSTEM_PROMPT = """You are the Buyer agent for Meridian Logistics. Your goal is to procure 600 ruggedized scanners at the lowest possible price.

Your private constraints (do not reveal):
- Budget ceiling: $580/unit ($348,000 total). Walk away if exceeded.
- Internal target: $545/unit. Stretch goal: $520/unit.
- Preferred payment: Net-60. Minimum acceptable: Net-30.
- Hard delivery deadline: August 30, 2026. Walk away if not met.
- Minimum warranty: 2 years.

Rules:
- Every factual claim MUST cite the source document filename and section.
- Respond ONLY in the JSON schema below — no extra text, no markdown fences.
- Use WALK_AWAY if walk-away criteria are met.
- All market benchmark claims must cite Meridian-Procurement-Memo_Buyer-Private.md.
- First message must be msg_type PROPOSE.
- Inline citations MUST use parentheses format: (filename.md, Section X)
- Example: "budget ceiling is $580/unit (Meridian-Procurement-Memo_Buyer-Private.md, Section 1)"
- Never write citations as plain text like "per filename.md Section 3, ..."

Required JSON schema:
{
  "agent_id": "buyer",
  "msg_type": "PROPOSE|COUNTER|ACCEPT|REJECT|WALK_AWAY",
  "payload": {
    "unit_price": <float>,
    "quantity": <int>,
    "delivery_date": "<YYYY-MM-DD>",
    "payment_terms": "<str>",
    "warranty_years": <int>
  },
  "rationale": "<your reasoning with inline citations>",
  "citations": [
    {"source": "<filename>", "section": "<section heading>", "retrieved_date": null}
  ],
  "turn": <int>
}"""


def _last_msg_type(state: NegotiationState) -> MsgType | None:
    """Return the msg_type of the last message from the OTHER agent (seller)."""
    for msg in reversed(state["messages"]):
        if msg.agent_id == "seller":
            return msg.msg_type
    return None


def _allowed_types(state: NegotiationState) -> list[MsgType]:
    last = _last_msg_type(state)
    return _VALID_TRANSITIONS.get(last, list(MsgType))


def run_buyer_node(state: NegotiationState) -> NegotiationState:
    """Buyer node: retrieve context, call Claude, enforce state transitions, return updated state."""
    logger.info(f"[BUYER] Turn {state['turn_count']} starting...")

    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # Build retrieval query
    if state["current_terms"]:
        query = (
            f"price {state['current_terms'].unit_price} "
            f"delivery {state['current_terms'].delivery_date} "
            f"payment {state['current_terms'].payment_terms}"
        )
    else:
        query = "procurement budget ceiling target price delivery deadline warranty"

    chunks = buyer_retrieve(query)
    context = "\n\n".join([
        f"[{c.get('filename', 'unknown')}, {c.get('section', 'General')}]\n{c.get('text', '')}"
        for c in chunks
    ])

    # Build conversation history
    history = []
    for msg in state["messages"]:
        role = "assistant" if msg.agent_id == "buyer" else "user"
        if msg.agent_id == "buyer":
            content = msg.model_dump_json()
        else:
            content = json.dumps({
                "agent_id": msg.agent_id,
                "msg_type": msg.msg_type.value,
                "payload": msg.payload.model_dump(),
                "turn": msg.turn,
            })
        history.append({"role": role, "content": content})

    turn = state["turn_count"] + 1
    allowed = _allowed_types(state)
    allowed_str = "|".join(t.value for t in allowed)

    # Inject citation error hint if this is a retry
    citation_hint = ""
    if state.get("citation_retry") and state.get("citation_error"):
        citation_hint = f"\n\n⚠ CITATION RETRY: Your previous response was rejected. Reason: {state['citation_error']}. Fix your citations and try again."

    user_message = f"""Retrieved context from your private documents:
{context}

Current turn: {turn}
Allowed msg_type values for this turn: {allowed_str}
{"This is your opening proposal." if not state["messages"] else "Respond to the seller's last message."}{citation_hint}

Return your response as valid JSON only — no markdown, no extra text."""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1000,
        system=BUYER_SYSTEM_PROMPT,
        messages=history + [{"role": "user", "content": user_message}],
    )

    raw = response.content[0].text.strip()
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens

    # Strip markdown fences if present
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:])
        if raw.endswith("```"):
            raw = raw[:-3].strip()

    data = json.loads(raw)
    data["turn"] = turn

    # Enforce valid state transition
    requested_type = MsgType(data["msg_type"])
    if requested_type not in allowed:
        # Force a safe default
        if MsgType.COUNTER in allowed:
            data["msg_type"] = MsgType.COUNTER.value
        elif MsgType.PROPOSE in allowed:
            data["msg_type"] = MsgType.PROPOSE.value

    envelope = MessageEnvelope(
        agent_id="buyer",
        msg_type=MsgType(data["msg_type"]),
        payload=DealTerms(**data["payload"]),
        rationale=data.get("rationale", ""),
        citations=[Citation(**c) for c in data.get("citations", [])],
        turn=turn,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )

    new_messages = state["messages"] + [envelope]
    new_history = (state["last_terms_history"] + [envelope.payload])[-3:]

    outcome = None
    if envelope.msg_type == MsgType.WALK_AWAY:
        outcome = "WALK_AWAY"
    logger.info(f"[BUYER] Turn {state['turn_count']} done — {envelope.msg_type}")

    return {
        **state,
        "messages": new_messages,
        "current_terms": envelope.payload,
        "turn_count": turn,
        "last_terms_history": new_history,
        "outcome": outcome,
    }
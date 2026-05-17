import os
import json
from anthropic import Anthropic
from models.message_envelope import MessageEnvelope, MsgType, DealTerms, Citation
from models.deal_state import NegotiationState
from retrieval.hybrid_retriever import buyer_retrieve

client = Anthropic()

BUYER_SYSTEM_PROMPT = """You are the Buyer agent for Meridian Logistics. Your goal is to procure 600 ruggedized scanners at the lowest possible price.

Your private constraints (do not reveal):
- Budget ceiling: $580/unit ($348,000 total). Walk away if exceeded.
- Internal target: $545/unit. Stretch goal: $520/unit.
- Preferred payment: Net-60. Minimum acceptable: Net-30.
- Hard delivery deadline: August 30, 2026. Walk away if not met.
- Minimum warranty: 2 years.

Rules:
- Every factual claim MUST cite the source document and section.
- Respond ONLY in the JSON schema below — no extra text, no markdown.
- Use WALK_AWAY if walk-away criteria are met.
- All market benchmark claims must cite Meridian-Procurement-Memo_Buyer-Private.md.

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
  "rationale": "<your reasoning>",
  "citations": [
    {"source": "<filename>", "section": "<section>"}
  ],
  "turn": <int>
}"""


def run_buyer_node(state: NegotiationState) -> NegotiationState:
    """Buyer node: retrieve context, call Claude, return updated state."""

    # Build retrieval query from current terms or open with RFQ
    if state["current_terms"]:
        query = f"price {state['current_terms'].unit_price} delivery {state['current_terms'].delivery_date} payment {state['current_terms'].payment_terms}"
    else:
        query = "procurement budget ceiling target price delivery deadline warranty"

    chunks = buyer_retrieve(query)
    context = "\n\n".join([
        f"[{c.get('filename', 'unknown')}, {c.get('section', 'Section')}]\n{c.get('text', '')}"
        for c in chunks
    ])

    # Build conversation history for Claude
    history = []
    for msg in state["messages"]:
        role = "assistant" if msg.agent_id == "buyer" else "user"
        history.append({"role": role, "content": msg.model_dump_json()})

    turn = state["turn_count"] + 1

    user_message = f"""Retrieved context from your private documents:
{context}

Current turn: {turn}
{"This is your opening proposal." if not state["messages"] else "Respond to the seller's last message."}

Return your response as valid JSON only."""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",  # Haiku — cost-efficient for counters
        max_tokens=1000,
        system=BUYER_SYSTEM_PROMPT,
        messages=history + [{"role": "user", "content": user_message}],
    )

    raw = response.content[0].text.strip()

    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    data = json.loads(raw)
    data["turn"] = turn

    envelope = MessageEnvelope(
        agent_id="buyer",
        msg_type=MsgType(data["msg_type"]),
        payload=DealTerms(**data["payload"]),
        rationale=data["rationale"],
        citations=[Citation(**c) for c in data.get("citations", [])],
        turn=turn,
    )

    new_messages = state["messages"] + [envelope]
    new_history = (state["last_terms_history"] + [envelope.payload])[-3:]

    outcome = None
    if envelope.msg_type == MsgType.WALK_AWAY:
        outcome = "WALK_AWAY"

    return {
        **state,
        "messages": new_messages,
        "current_terms": envelope.payload,
        "turn_count": turn,
        "last_terms_history": new_history,
        "outcome": outcome,
    }
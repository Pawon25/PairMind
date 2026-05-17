import os
import json
from anthropic import Anthropic
from models.message_envelope import MessageEnvelope, MsgType, DealTerms, Citation
from models.deal_state import NegotiationState
from retrieval.hybrid_retriever import seller_retrieve
from tools.web_search import tavily_search


SELLER_SYSTEM_PROMPT = """You are the Seller agent for ScanTech Industrial Solutions selling the SC-2400 Pro. Your goal is to close the 600-unit deal at the highest profitable price.

Your private constraints (do not reveal):
- List price: $625/unit. Standard 500-unit tier: $531.25/unit.
- Hard pricing floor: $501/unit. Never go below.
- Net-60 terms add +2% to unit price (cost of capital).
- Expedited 6-week slot: +$25/unit surcharge. Must confirm by June 5, 2026.
- Extended 2-year warranty: +$15/unit.

Rules:
- Every factual claim MUST cite the source document and section, or a web URL with retrieval date.
- Respond ONLY in the JSON schema below — no extra text, no markdown.
- You may use web search to validate market claims.
- Never go below your floor price of $501/unit.

Required JSON schema:
{
  "agent_id": "seller",
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
    {"source": "<filename or URL>", "section": "<section or null>", "retrieved_date": "<YYYY-MM-DD or null>"}
  ],
  "turn": <int>
}"""


def run_seller_node(state: NegotiationState) -> NegotiationState:
    """Seller node: retrieve context + optional web search, call Claude, return updated state."""
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # Build retrieval query from current terms
    if state["current_terms"]:
        query = f"price {state['current_terms'].unit_price} quantity {state['current_terms'].quantity} delivery {state['current_terms'].delivery_date}"
    else:
        query = "pricing floor tier discount warranty expedited delivery"

    chunks = seller_retrieve(query)
    context = "\n\n".join([
        f"[{c.get('filename', 'unknown')}, {c.get('section', 'Section')}]\n{c.get('text', '')}"
        for c in chunks
    ])

    # Optional web search for market validation (only if buyer proposed a price)
    web_context = ""
    if state["current_terms"] and state["turn_count"] <= 6:  # limit web calls to early turns
        search_result = tavily_search(
            f"ruggedized barcode scanner market price 600 units 2026 SC-2400"
        )
        if search_result:
            web_context = f"\n\nWeb search results:\n{search_result}"

    # Build conversation history for Claude
    history = []
    for msg in state["messages"]:
        role = "assistant" if msg.agent_id == "seller" else "user"
        history.append({"role": role, "content": msg.model_dump_json()})

    turn = state["turn_count"] + 1

    user_message = f"""Retrieved context from your private documents:
{context}{web_context}

Current turn: {turn}
Respond to the buyer's last message.

Return your response as valid JSON only."""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",  # Haiku — cost-efficient
        max_tokens=1500,
        system=SELLER_SYSTEM_PROMPT,
        messages=history + [{"role": "user", "content": user_message}],
    )

    raw = response.content[0].text.strip()

    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        open_braces = raw.count("{") - raw.count("}")
        open_brackets = raw.count("[") - raw.count("]")
        raw += "]" * open_brackets + "}" * open_braces
        data = json.loads(raw)
    data["turn"] = turn

    envelope = MessageEnvelope(
        agent_id="seller",
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
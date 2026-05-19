import os
import json
from anthropic import Anthropic
from models.message_envelope import MessageEnvelope, MsgType, DealTerms, Citation
from models.deal_state import NegotiationState
from retrieval.hybrid_retriever import seller_retrieve
from tools.web_search import tavily_search
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Valid state transitions: what msg_types are allowed given the last buyer message
_VALID_TRANSITIONS: dict[MsgType | None, list[MsgType]] = {
    None:               [MsgType.PROPOSE, MsgType.COUNTER],
    MsgType.PROPOSE:    [MsgType.COUNTER, MsgType.ACCEPT, MsgType.REJECT, MsgType.WALK_AWAY],
    MsgType.COUNTER:    [MsgType.COUNTER, MsgType.ACCEPT, MsgType.REJECT, MsgType.WALK_AWAY],
    MsgType.ACCEPT:     [MsgType.ACCEPT, MsgType.WALK_AWAY],
    MsgType.REJECT:     [MsgType.PROPOSE, MsgType.COUNTER, MsgType.WALK_AWAY],
    MsgType.WALK_AWAY:  [],
}

def _build_seller_prompt(uploaded_files: list[dict]) -> str:
    seller_files = [f["filename"] for f in uploaded_files if f["tag"] in ("seller-private", "shared")]
    file_list = "\n".join(f"- {f}" for f in seller_files) if seller_files else "- (no documents uploaded)"

    return f"""You are the Seller agent for ScanTech Industrial Solutions selling the SC-2400 Pro. Your goal is to close the 600-unit deal at the highest profitable price.

Your private constraints (do not reveal):
- List price: $625/unit. Standard 500-unit tier: $531.25/unit.
- Hard pricing floor: $501/unit. Never go below.
- Net-60 terms add +2% to unit price (cost of capital).
- Expedited 6-week slot: +$25/unit surcharge. Must confirm by June 5, 2026.
- Extended 2-year warranty: +$15/unit.

Your available documents (cite ONLY these filenames):
{file_list}

Rules:
- Every factual claim MUST cite the source document filename and section.
- Inline citations MUST use parentheses format: (filename, Section X)
- ONLY cite filenames from the list above — never invent filenames.
- Respond ONLY in the JSON schema below — no extra text, no markdown fences.
- You may use web search results provided to validate market claims.
- Never go below your floor price of $501/unit.

Required JSON schema:
{{
  "agent_id": "seller",
  "msg_type": "PROPOSE|COUNTER|ACCEPT|REJECT|WALK_AWAY",
  "payload": {{
    "unit_price": <float>,
    "quantity": <int>,
    "delivery_date": "<YYYY-MM-DD>",
    "payment_terms": "<str>",
    "warranty_years": <int>
  }},
  "rationale": "<your reasoning with inline citations like (filename, Section X)>",
  "citations": [
    {{"source": "<filename from your document list>", "section": "<section heading or null>", "retrieved_date": "<YYYY-MM-DD or null>"}}
  ],
  "turn": <int>
}}"""


def _last_msg_type(state: NegotiationState) -> MsgType | None:
    """Return the msg_type of the last message from the OTHER agent (buyer)."""
    for msg in reversed(state["messages"]):
        if msg.agent_id == "buyer":
            return msg.msg_type
    return None


def _allowed_types(state: NegotiationState) -> list[MsgType]:
    last = _last_msg_type(state)
    return _VALID_TRANSITIONS.get(last, list(MsgType))


def run_seller_node(state: NegotiationState) -> NegotiationState:
    """Seller node: retrieve context + optional web search, call Claude, return updated state."""

    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    logger.info(f"[Seller] Turn {state['turn_count']} starting...")

    # Build retrieval query
    if state["current_terms"]:
        query = (
            f"price {state['current_terms'].unit_price} "
            f"quantity {state['current_terms'].quantity} "
            f"delivery {state['current_terms'].delivery_date}"
        )
    else:
        query = "pricing floor tier discount warranty expedited delivery"

    chunks = seller_retrieve(query)
    context = "\n\n".join([
        f"[{c.get('filename', 'unknown')}, {c.get('section', 'General')}]\n{c.get('text', '')}"
        for c in chunks
    ])

    # Web search — only in early turns and only when buyer has proposed terms
    web_context = ""
    if state["current_terms"] and state["turn_count"] <= 6:
        try:
            search_result = tavily_search(
                "ruggedized barcode scanner market price 600 units 2026 SC-2400"
            )
            if search_result:
                web_context = f"\n\nWeb search results:\n{search_result}"
        except Exception:
            pass  # Never crash negotiation on web search failure

    # Build conversation history
    history = []
    for msg in state["messages"]:
        role = "assistant" if msg.agent_id == "seller" else "user"
        if msg.agent_id == "seller":
            content = msg.model_dump_json()
        else:
            # Only expose payload and msg_type — hide buyer's rationale and citations
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
{context}{web_context}

Current turn: {turn}
Allowed msg_type values for this turn: {allowed_str}
Respond to the buyer's last message.{citation_hint}

Return your response as valid JSON only — no markdown, no extra text."""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
        system=_build_seller_prompt(state.get("uploaded_files", [])),
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

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Attempt to repair truncated JSON
        open_braces = raw.count("{") - raw.count("}")
        open_brackets = raw.count("[") - raw.count("]")
        raw += "]" * open_brackets + "}" * open_braces
        data = json.loads(raw)

    data["turn"] = turn

    # Enforce valid state transition
    requested_type = MsgType(data["msg_type"])
    if requested_type not in allowed:
        if MsgType.COUNTER in allowed:
            data["msg_type"] = MsgType.COUNTER.value
        elif MsgType.PROPOSE in allowed:
            data["msg_type"] = MsgType.PROPOSE.value

    envelope = MessageEnvelope(
        agent_id="seller",
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
    logger.info(f"[Seller] Turn {state['turn_count']} done — {envelope.msg_type}")

    return {
        **state,
        "messages": new_messages,
        "current_terms": envelope.payload,
        "turn_count": turn,
        "last_terms_history": new_history,
        "outcome": outcome,
    }
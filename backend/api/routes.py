import asyncio
import json
import tempfile
import time
import uuid
from pathlib import Path
from typing import AsyncGenerator

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agents.orchestrator import build_graph, build_summary
from models.deal_state import NegotiationState
from ingestion.loader import load_document
from ingestion.chunker import chunk_documents
from ingestion.embedder import embed_texts
from ingestion.opensearch_store import upsert_chunks

router = APIRouter()

# ── In-memory session store ───────────────────────────────────────────────────
# { session_id: { "state": NegotiationState, "events": list[dict], "done": bool, "summary": dict } }
_sessions: dict[str, dict] = {}

VALID_TAGS = {"buyer-private", "seller-private", "shared"}


# ── POST /upload ──────────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    doc_id: str
    filename: str
    tag: str
    chunks_indexed: int


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    tag: str = Form(...),
):
    if tag not in VALID_TAGS:
        raise HTTPException(400, f"Invalid tag '{tag}'. Must be one of: {', '.join(VALID_TAGS)}")

    suffix = Path(file.filename).suffix.lower()
    content = await file.read()

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        docs = load_document(tmp_path, tag=tag)
        for doc in docs:
            doc.metadata["filename"] = file.filename
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    chunks = chunk_documents(docs)
    if not chunks:
        raise HTTPException(422, f"No chunks extracted from '{file.filename}'. Check file content.")

    embeddings = embed_texts([c.page_content for c in chunks])
    upsert_chunks(chunks, embeddings)

    return UploadResponse(
        doc_id=str(uuid.uuid4()),
        filename=file.filename,
        tag=tag,
        chunks_indexed=len(chunks),
    )


# ── POST /negotiate ───────────────────────────────────────────────────────────

class NegotiateResponse(BaseModel):
    session_id: str


@router.post("/negotiate", response_model=NegotiateResponse)
async def start_negotiation():
    session_id = str(uuid.uuid4())

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

    _sessions[session_id] = {
        "state":   initial_state,
        "events":  [],
        "done":    False,
        "summary": None,
    }

    asyncio.create_task(_run_negotiation_task(session_id, initial_state))

    return NegotiateResponse(session_id=session_id)


async def _run_negotiation_task(session_id: str, initial_state: NegotiationState):
    session = _sessions[session_id]
    graph = build_graph()
    start = time.time()

    def run_graph():
        try:
            for state_snapshot in graph.stream(initial_state, stream_mode="values"):
                msgs = state_snapshot.get("messages", [])
                if not msgs:
                    continue

                last_msg = msgs[-1]
                already_sent = sum(1 for e in session["events"] if e.get("type") == "turn")
                if last_msg.turn <= already_sent:
                    continue

                session["state"] = state_snapshot
                session["events"].append({
                    "type":          "turn",
                    "turn":          last_msg.turn,
                    "agent_id":      last_msg.agent_id,
                    "msg_type":      last_msg.msg_type.value,
                    "payload":       last_msg.payload.model_dump(),
                    "rationale":     last_msg.rationale,
                    "citations":     [c.model_dump() for c in last_msg.citations],
                    "input_tokens":  last_msg.input_tokens,
                    "output_tokens": last_msg.output_tokens,
                })

            final_state = session["state"]
            duration = time.time() - start
            summary = build_summary(final_state, duration)
            summary["session_id"] = session_id
            session["summary"] = summary
            session["events"].append({"type": "summary", **summary})

        except Exception as e:
            import traceback
            session["events"].append({
                "type":    "error",
                "message": str(e),
                "detail":  traceback.format_exc(),
            })
        finally:
            session["done"] = True

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, run_graph)


# ── GET /negotiate/{id}/stream ────────────────────────────────────────────────

@router.get("/negotiate/{session_id}/stream")
async def stream_negotiation(session_id: str):
    if session_id not in _sessions:
        raise HTTPException(404, "Session not found")

    return StreamingResponse(
        _sse_generator(session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control":    "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


async def _sse_generator(session_id: str) -> AsyncGenerator[str, None]:
    session = _sessions[session_id]
    sent = 0

    while True:
        events = session["events"]

        while sent < len(events):
            yield f"data: {json.dumps(events[sent])}\n\n"
            sent += 1

        if session["done"] and sent >= len(session["events"]):
            yield 'data: {"type": "done"}\n\n'
            break

        await asyncio.sleep(0.25)


# ── GET /negotiate/{id}/state ─────────────────────────────────────────────────

@router.get("/negotiate/{session_id}/state")
async def get_state(session_id: str):
    if session_id not in _sessions:
        raise HTTPException(404, "Session not found")

    state = _sessions[session_id]["state"]
    current_terms = state.get("current_terms")

    return {
        "session_id":    session_id,
        "turn_count":    state.get("turn_count", 0),
        "outcome":       state.get("outcome"),
        "current_terms": current_terms.model_dump() if current_terms else None,
        "done":          _sessions[session_id]["done"],
    }


# ── GET /negotiate/{id}/summary ───────────────────────────────────────────────

@router.get("/negotiate/{session_id}/summary")
async def get_summary(session_id: str):
    if session_id not in _sessions:
        raise HTTPException(404, "Session not found")

    session = _sessions[session_id]
    if not session["done"]:
        raise HTTPException(202, "Negotiation still in progress")

    return session["summary"]
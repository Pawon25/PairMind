import asyncio
import json
import tempfile
import time
import uuid
from pathlib import Path
from typing import AsyncGenerator

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, Depends
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from agents.orchestrator import build_graph, build_summary
from models.deal_state import NegotiationState
from ingestion.loader import load_document
from ingestion.chunker import chunk_documents
from ingestion.embedder import embed_texts
from ingestion.opensearch_store import upsert_chunks, fetch_citation_snippet, delete_session_chunks
from auth.tokens import check_token, consume_negotiation, TokenError
from demo_requests_store import save_request

router = APIRouter()

_bearer = HTTPBearer(auto_error=False)


def _require_valid_token(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> str:
    """Gate dependency for /upload - valid + unexpired, doesn't burn negotiation quota."""
    if creds is None:
        raise HTTPException(401, "Missing access token")
    try:
        check_token(creds.credentials)
    except TokenError as e:
        raise HTTPException(401, str(e))
    return creds.credentials


def _require_and_consume_negotiation(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> str:
    """Gate dependency for /negotiate - the only endpoint that spends a use."""
    if creds is None:
        raise HTTPException(401, "Missing access token")
    try:
        consume_negotiation(creds.credentials)
    except TokenError as e:
        raise HTTPException(401, str(e))
    return creds.credentials

# ── In-memory session store ───────────────────────────────────────────────────
# { session_id: { "state": NegotiationState, "events": list[dict], "done": bool, "summary": dict } }
_sessions: dict[str, dict] = {}
# Staged uploads awaiting /negotiate, keyed by session_id (one browser session's
# corpus) - NOT a shared global list, so concurrent visitors' uploads don't mix.
_staged_files: dict[str, list[dict]] = {}


VALID_TAGS = {"buyer-private", "seller-private", "shared"}


# ── POST /auth/verify-token ──────────────────────────────────────────────────

class VerifyTokenResponse(BaseModel):
    valid: bool
    uses_remaining: int
    expires_at: str


@router.post("/auth/verify-token", response_model=VerifyTokenResponse)
async def verify_token(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)):
    """Gate check for the landing page - validates without consuming a use."""
    if creds is None:
        raise HTTPException(401, "Missing access token")
    try:
        row = check_token(creds.credentials)
    except TokenError as e:
        raise HTTPException(401, str(e))
    return VerifyTokenResponse(
        valid=True,
        uses_remaining=row["uses_remaining"],
        expires_at=row["expires_at"],
    )


# ── POST /demo-request ───────────────────────────────────────────────────────
# No auth - this is the entry point for people who don't have a token yet.

class DemoRequestBody(BaseModel):
    name: str
    email: str
    message: str = ""


@router.post("/demo-request")
async def create_demo_request(body: DemoRequestBody):
    if not body.name.strip() or not body.email.strip():
        raise HTTPException(400, "Name and email are required")
    save_request(body.name.strip(), body.email.strip(), body.message.strip())
    return {"status": "received"}


# ── POST /upload ──────────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    doc_id: str
    filename: str
    tag: str
    chunks_indexed: int


def _ingest_document(path: str, tag: str, filename: str, session_id: str) -> int:
    """Load, chunk, embed, and index one document under session_id. Returns chunks indexed.
    Shared by /upload (an uploaded file, path is a temp copy) and /upload-sample
    (a path already on disk).
    """
    docs = load_document(path, tag=tag)
    for doc in docs:
        doc.metadata["filename"] = filename

    chunks = chunk_documents(docs)
    if not chunks:
        raise HTTPException(422, f"No chunks extracted from '{filename}'. Check file content.")

    embeddings = embed_texts([c.page_content for c in chunks])
    upsert_chunks(chunks, embeddings, session_id)
    _staged_files.setdefault(session_id, []).append({"filename": filename, "tag": tag})
    return len(chunks)


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    tag: str = Form(...),
    session_id: str = Form(...),
    _token: str = Depends(_require_valid_token),
):
    if tag not in VALID_TAGS:
        raise HTTPException(400, f"Invalid tag '{tag}'. Must be one of: {', '.join(VALID_TAGS)}")
    suffix = Path(file.filename).suffix.lower()
    content = await file.read()

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        chunks_indexed = _ingest_document(tmp_path, tag, file.filename, session_id)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return UploadResponse(
        doc_id=str(uuid.uuid4()),
        filename=file.filename,
        tag=tag,
        chunks_indexed=chunks_indexed,
    )


# ── POST /upload-sample ──────────────────────────────────────────────────────
# Loads the built-in sample corpus into this session - lets a visitor skip
# hunting for their own documents and go straight to a live negotiation.

SAMPLE_DOCS = [
    {"filename": "Meridian-Procurement-Memo_Buyer-Private.md", "tag": "buyer-private"},
    {"filename": "RFQ-2026-MER-0847_Shared.md", "tag": "shared"},
    {"filename": "ScanTech-Pricing-Sheet_Seller-Private.md", "tag": "seller-private"},
]
SAMPLE_DOCS_DIR = Path(__file__).resolve().parent.parent.parent / "data"


@router.post("/upload-sample", response_model=list[UploadResponse])
async def upload_sample_documents(
    session_id: str = Form(...),
    _token: str = Depends(_require_valid_token),
):
    responses = []
    for doc in SAMPLE_DOCS:
        path = SAMPLE_DOCS_DIR / doc["filename"]
        chunks_indexed = _ingest_document(str(path), doc["tag"], doc["filename"], session_id)
        responses.append(UploadResponse(
            doc_id=str(uuid.uuid4()),
            filename=doc["filename"],
            tag=doc["tag"],
            chunks_indexed=chunks_indexed,
        ))
    return responses


# ── POST /negotiate ───────────────────────────────────────────────────────────

class NegotiateResponse(BaseModel):
    session_id: str



@router.post("/negotiate", response_model=NegotiateResponse)
async def start_negotiation(session_id: str = Form(...), _token: str = Depends(_require_and_consume_negotiation)):
    # session_id is client-generated (same one used for /upload calls) so the
    # negotiation retrieves from exactly this browser session's own documents,
    # not the whole shared index.
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
        "uploaded_files": list(_staged_files.get(session_id, []))
    }

    _sessions[session_id] = {
        "state":   initial_state,
        "events":  [],
        "done":    False,
        "summary": None,
    }
    _staged_files.pop(session_id, None)

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

@router.get("/citation")
async def get_citation_snippet(source: str, section: str = ""):
    snippet = fetch_citation_snippet(source, section)
    if not snippet:
        raise HTTPException(404, "Citation snippet not found")
    return {"source": source, "section": section, "snippet": snippet}

@router.post("/reset")
async def reset_session(session_id: str = Form(...)):
    # Scoped to this session only - previously this dropped the entire shared
    # index, which would wipe every other visitor's in-progress negotiation too.
    delete_session_chunks(session_id)
    _staged_files.pop(session_id, None)
    return {"status": "ready"}
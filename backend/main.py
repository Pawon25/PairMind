from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router
from ingestion.opensearch_store import create_index_if_not_exists


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle handler (replaces deprecated @app.on_event)."""
    create_index_if_not_exists()
    yield


app = FastAPI(title="PairMind", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok"}
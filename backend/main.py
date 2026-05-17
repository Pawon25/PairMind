from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router
from ingestion.opensearch_store import create_index_if_not_exists
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")
app = FastAPI(title="PairMind", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    create_index_if_not_exists()

app.include_router(router)

@app.get("/health")
async def health():
    return {"status": "ok"}
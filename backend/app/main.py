from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import ingest
from app.services.embedding import get_embedder
from app.services.vectorstore import ensure_collection


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Create collection + payload indexes if needed (idempotent).
    await ensure_collection()
    # Pre-warm the embedder so first request doesn't pay the 133MB
    # model download as latency.
    get_embedder()
    yield


app = FastAPI(title="Reel Compare RAG", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router, prefix="/api/v1/ingest", tags=["ingest"])


@app.get("/health")
async def health():
    return {"status": "ok"}
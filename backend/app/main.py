from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import chat, ingest
from app.services.embedding import get_embedder
from app.services.vectorstore import ensure_collection


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await ensure_collection()
    get_embedder()  # pre-warm so first request doesn't pay model-download latency
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
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])


@app.get("/health")
async def health():
    return {"status": "ok"}
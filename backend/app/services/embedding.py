from __future__ import annotations

from functools import lru_cache

from fastembed import TextEmbedding


# BGE-small-en-v1.5: 384 dims, ~133MB, MTEB top-tier for retrieval.
EMBED_MODEL = "BAAI/bge-small-en-v1.5"
EMBED_DIM = 384


@lru_cache(maxsize=1)
def get_embedder() -> TextEmbedding:
    """Singleton. First call downloads ~133MB to ~/.cache/fastembed/."""
    return TextEmbedding(model_name=EMBED_MODEL)


def embed_texts(texts: list[str]) -> list[list[float]]:
    embedder = get_embedder()
    return [vec.tolist() for vec in embedder.embed(texts)]


def embed_query(query: str) -> list[float]:
    embedder = get_embedder()
    return next(iter(embedder.embed([query]))).tolist()
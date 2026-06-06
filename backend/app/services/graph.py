from __future__ import annotations

from typing import TypedDict
import asyncio
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from app.config import settings
from app.services import vectorstore
from app.services.embedding import embed_query


class State(TypedDict):
    session_id: str
    video_ids: list[str]
    user_message: str
    history: list[BaseMessage]
    retrieved: list[dict]
    response: str


BASE_SYSTEM = """You are a creator-analytics assistant comparing short-form videos (YouTube Shorts and Instagram Reels).

You have retrieved context from one or two videos the user is comparing. Your job is to answer their question grounded in that context.

Rules:
- ALWAYS cite sources using [Source N] notation matching the chunk numbering below.
- When comparing engagement, hooks, or content, ground every claim in cited chunks.
- If the retrieved context doesn't contain enough to answer, say so directly — don't fabricate.
- Be concise. Creator-tools users want signal, not essays."""


def _build_system_prompt(retrieved: list[dict]) -> str:
    if not retrieved:
        return BASE_SYSTEM + "\n\nNo relevant context retrieved."

    blocks = []
    for i, c in enumerate(retrieved, start=1):
        blocks.append(
            f"[Source {i}] video={c['video_id']} platform={c.get('platform')} "
            f"creator={c.get('creator')!r} engagement={c.get('engagement_rate', 0)}% "
            f"time={c.get('start_time', 0):.1f}s-{c.get('end_time', 0):.1f}s\n"
            f"  \"{c.get('text', '')}\""
        )
    return BASE_SYSTEM + "\n\nRetrieved context:\n" + "\n\n".join(blocks)


async def retrieve_node(state: State) -> dict:
    """
    Retrieve relevant chunks for the user query.

    When comparing N specific videos (the normal case), we retrieve top-k
    PER VIDEO in parallel and merge. Otherwise the global top-k can starve
    one side of the comparison — a video with fewer total chunks (e.g. a
    short Reel vs a long Short) or one whose vocabulary is less aligned
    with the query will produce zero citations and the LLM can't compare.

    When no video filter is given, fall back to a single global search.
    """
    query_vec = embed_query(state["user_message"])
    video_ids = state["video_ids"]

    if not video_ids:
        return {"retrieved": await vectorstore.search(query_vec, top_k=6)}

    per_video_k = max(3, 6 // len(video_ids))  # 3 each for 2 videos, etc.
    results = await asyncio.gather(*[
        vectorstore.search(query_vec, video_ids=[vid], top_k=per_video_k)
        for vid in video_ids
    ])
    # Flatten, preserving per-video order (so [Source 1-3] are video A, [4-6] video B)
    return {"retrieved": [c for batch in results for c in batch]}


async def generate_node(state: State) -> dict:
    """
    Call GPT-4o-mini. Token-level streaming is captured by the caller
    via astream_events; this node returns the assembled response.
    """
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY not set in .env")

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.3,
        streaming=True,
        api_key=settings.openai_api_key,
    )

    messages: list[BaseMessage] = [
        SystemMessage(content=_build_system_prompt(state["retrieved"])),
        *state["history"][-10:],  # cap history; 10 turns is plenty for this UX
        HumanMessage(content=state["user_message"]),
    ]

    result = await llm.ainvoke(messages)
    return {"response": result.content}


def _build_graph():
    g = StateGraph(State)
    g.add_node("retrieve", retrieve_node)
    g.add_node("generate", generate_node)
    g.set_entry_point("retrieve")
    g.add_edge("retrieve", "generate")
    g.add_edge("generate", END)
    return g.compile()


# Compile once at import. Compilation is cheap but non-zero; doing it
# per-request becomes a real latency tax at scale.
_GRAPH = None


def get_graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = _build_graph()
    return _GRAPH
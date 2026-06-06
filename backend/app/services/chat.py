from __future__ import annotations

import json
from typing import AsyncGenerator

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from app.services.graph import get_graph


# In-memory session store, keyed by session_id → list of LangChain
# messages. Day-3 simple; swap to Redis when we go multi-instance.
_SESSIONS: dict[str, list[BaseMessage]] = {}


def get_history(session_id: str) -> list[BaseMessage]:
    return _SESSIONS.get(session_id, [])


def append_turn(session_id: str, user: str, assistant: str) -> None:
    history = _SESSIONS.setdefault(session_id, [])
    history.append(HumanMessage(content=user))
    history.append(AIMessage(content=assistant))
    # Cap memory to avoid unbounded growth (20 turns = 40 messages)
    if len(history) > 40:
        _SESSIONS[session_id] = history[-40:]


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


async def stream_chat(
    session_id: str,
    video_ids: list[str],
    user_message: str,
) -> AsyncGenerator[str, None]:
    """
    Drive the LangGraph and stream SSE events:
      - citations: emitted once after retrieval (lets frontend render
        citation chips before tokens arrive)
      - token: one per LLM chunk
      - done: terminal event with full response length
      - error: any failure mid-stream
    """
    graph = get_graph()
    history = get_history(session_id)

    initial_state = {
        "session_id": session_id,
        "video_ids": video_ids,
        "user_message": user_message,
        "history": history,
        "retrieved": [],
        "response": "",
    }

    citations_sent = False
    full_response = ""

    try:
        async for event in graph.astream_events(initial_state, version="v2"):
            kind = event["event"]
            name = event.get("name", "")

            if (
                kind == "on_chain_end"
                and name == "retrieve"
                and not citations_sent
            ):
                chunks = event["data"]["output"].get("retrieved", [])
                yield _sse({
                    "type": "citations",
                    "chunks": [
                        {
                            "source_index": i + 1,
                            "video_id": c.get("video_id"),
                            "platform": c.get("platform"),
                            "creator": c.get("creator"),
                            "position": c.get("position"),
                            "start_time": c.get("start_time"),
                            "end_time": c.get("end_time"),
                            "text": c.get("text"),
                            "score": c.get("score"),
                        }
                        for i, c in enumerate(chunks)
                    ],
                })
                citations_sent = True

            elif kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    full_response += content
                    yield _sse({"type": "token", "text": content})

        append_turn(session_id, user_message, full_response)
        yield _sse({"type": "done", "length": len(full_response)})

    except Exception as e:
        yield _sse({"type": "error", "message": f"{type(e).__name__}: {e}"})
import type { IngestResponse, SSEEvent } from '../types';

const API_BASE = '/api/v1';

export async function ingestVideo(url: string): Promise<IngestResponse> {
  const res = await fetch(`${API_BASE}/ingest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(detail.detail || 'Ingestion failed');
  }
  return res.json();
}

/**
 * Stream chat events from the backend SSE endpoint.
 *
 * Using fetch + ReadableStream (not EventSource) because:
 * - EventSource is GET-only, our endpoint takes a JSON body.
 * - This is the de-facto pattern for LLM streaming UIs in 2024-26.
 */
export async function* streamChat(
  sessionId: string,
  videoIds: string[],
  message: string
): AsyncGenerator<SSEEvent> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, video_ids: videoIds, message }),
  });
  if (!res.ok || !res.body) throw new Error(`Chat request failed: ${res.statusText}`);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // SSE messages are separated by blank lines (\n\n).
    const parts = buffer.split('\n\n');
    buffer = parts.pop() || '';

    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith('data:')) continue;
      const json = line.slice(5).trim();
      if (!json) continue;
      try {
        yield JSON.parse(json) as SSEEvent;
      } catch {
        // Malformed chunk — skip
      }
    }
  }
}
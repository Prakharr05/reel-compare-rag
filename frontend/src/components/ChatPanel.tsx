import { useState, useRef, useEffect } from 'react';
import { streamChat } from '../lib/api';
import type { ChatMessage, Citation } from '../types';

interface Props {
  sessionId: string;
  videoIds: string[];
}

export function ChatPanel({ sessionId, videoIds }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streaming]);

  async function handleSend() {
    if (!input.trim() || streaming) return;
    const userMsg = input.trim();
    setInput('');

    setMessages((prev) => [
      ...prev,
      { role: 'user', content: userMsg },
      { role: 'assistant', content: '', citations: [] },
    ]);
    setStreaming(true);

    try {
      for await (const event of streamChat(sessionId, videoIds, userMsg)) {
        if (event.type === 'citations') {
          setMessages((prev) => {
            const u = [...prev];
            u[u.length - 1] = { ...u[u.length - 1], citations: event.chunks };
            return u;
          });
        } else if (event.type === 'token') {
          setMessages((prev) => {
            const u = [...prev];
            const last = u[u.length - 1];
            u[u.length - 1] = { ...last, content: last.content + event.text };
            return u;
          });
        } else if (event.type === 'error') {
          setMessages((prev) => {
            const u = [...prev];
            u[u.length - 1] = { ...u[u.length - 1], content: `Error: ${event.message}` };
            return u;
          });
        }
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Stream failed';
      setMessages((prev) => {
        const u = [...prev];
        u[u.length - 1] = { ...u[u.length - 1], content: `Error: ${msg}` };
        return u;
      });
    } finally {
      setStreaming(false);
    }
  }

  const ready = videoIds.length > 0;

  return (
    <div className="flex flex-col h-full rounded-lg border border-neutral-800 bg-neutral-900">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-sm text-neutral-500 py-12">
            {ready
              ? 'Ask about the videos. Try: "Why did one get more engagement than the other?"'
              : 'Ingest at least one video to start chatting.'}
          </div>
        )}
        {messages.map((msg, i) => <Message key={i} msg={msg} />)}
        <div ref={bottomRef} />
      </div>

      <div className="border-t border-neutral-800 p-3 flex gap-2">
        <input
          type="text"
          placeholder={ready ? 'Ask about the videos...' : 'Ingest a video first'}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          disabled={!ready || streaming}
          className="flex-1 px-3 py-2 text-sm rounded bg-neutral-950 border border-neutral-800 focus:border-neutral-600 outline-none disabled:opacity-50"
        />
        <button
          onClick={handleSend}
          disabled={!ready || !input.trim() || streaming}
          className="px-4 py-2 text-sm font-medium rounded bg-neutral-100 text-neutral-900 hover:bg-white disabled:opacity-30 disabled:cursor-not-allowed"
        >
          {streaming ? '...' : 'Send'}
        </button>
      </div>
    </div>
  );
}

function Message({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === 'user';
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[85%] rounded-lg px-4 py-2 text-sm ${
        isUser ? 'bg-neutral-100 text-neutral-900' : 'bg-neutral-800 text-neutral-100'
      }`}>
        <div className="whitespace-pre-wrap">{msg.content || '…'}</div>
        {msg.citations && msg.citations.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-3 pt-3 border-t border-neutral-700">
            {msg.citations.map((c) => <CitationChip key={c.source_index} c={c} />)}
          </div>
        )}
      </div>
    </div>
  );
}

function CitationChip({ c }: { c: Citation }) {
  const ts = `${Math.floor(c.start_time)}s`;
  return (
    <span
      title={c.text}
      className="text-xs px-2 py-0.5 rounded bg-neutral-700 text-neutral-300 cursor-help"
    >
      [{c.source_index}] {c.platform === 'youtube' ? 'YT' : 'IG'} · {ts}
    </span>
  );
}
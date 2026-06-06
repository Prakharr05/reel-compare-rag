import { useState } from 'react';
import { VideoCard } from './components/VideoCard';
import { ChatPanel } from './components/ChatPanel';
import { useSession } from './hooks/useSession';
import type { IngestResponse } from './types';

export default function App() {
  const sessionId = useSession();
  const [videoA, setVideoA] = useState<IngestResponse | null>(null);
  const [videoB, setVideoB] = useState<IngestResponse | null>(null);

  const videoIds = [
    videoA?.video.metadata.video_id,
    videoB?.video.metadata.video_id,
  ].filter((x): x is string => Boolean(x));

  return (
    <div className="h-screen flex flex-col">
      <header className="border-b border-neutral-800 px-6 py-3">
        <h1 className="text-lg font-semibold">Reel Compare RAG</h1>
        <p className="text-xs text-neutral-500">
          Compare engagement and content across YouTube Shorts and Instagram Reels
        </p>
      </header>

      <main className="flex-1 grid grid-rows-[auto_1fr] gap-4 p-4 overflow-hidden">
        <div className="grid grid-cols-2 gap-4">
          <VideoCard label="A" onIngested={setVideoA} />
          <VideoCard label="B" onIngested={setVideoB} />
        </div>
        <ChatPanel sessionId={sessionId} videoIds={videoIds} />
      </main>
    </div>
  );
}
import { useState } from 'react';
import { ingestVideo } from '../lib/api';
import type { IngestResponse } from '../types';

interface Props {
  label: 'A' | 'B';
  onIngested: (response: IngestResponse) => void;
}

const fmt = (n: number) =>
  n >= 1e6 ? `${(n / 1e6).toFixed(1)}M` :
  n >= 1e3 ? `${(n / 1e3).toFixed(1)}K` : `${n}`;

export function VideoCard({ label, onIngested }: Props) {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<IngestResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleIngest() {
    setLoading(true);
    setError(null);
    try {
      const result = await ingestVideo(url);
      setData(result);
      onIngested(result);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to ingest');
    } finally {
      setLoading(false);
    }
  }

  const m = data?.video.metadata;

  return (
    <div className="flex flex-col gap-3 p-4 rounded-lg border border-neutral-800 bg-neutral-900">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-neutral-400">Video {label}</h2>
        {data && (
          <span className="text-xs px-2 py-0.5 rounded bg-green-900/30 text-green-400">
            {data.chunks_indexed} chunks indexed
          </span>
        )}
      </div>

      <div className="flex gap-2">
        <input
          type="url"
          placeholder="YouTube Short or Instagram Reel URL"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          disabled={loading}
          className="flex-1 px-3 py-2 text-sm rounded bg-neutral-950 border border-neutral-800 focus:border-neutral-600 outline-none"
        />
        <button
          onClick={handleIngest}
          disabled={!url || loading}
          className="px-4 py-2 text-sm font-medium rounded bg-neutral-100 text-neutral-900 hover:bg-white disabled:opacity-30 disabled:cursor-not-allowed"
        >
          {loading ? '...' : 'Ingest'}
        </button>
      </div>

      {error && <div className="text-xs text-red-400">{error}</div>}

      {m && (
        <div className="flex gap-3">
          {m.thumbnail_url && (
            <img src={m.thumbnail_url} alt="" className="w-20 h-32 object-cover rounded bg-neutral-800" />
          )}
          <div className="flex-1 text-sm space-y-1 min-w-0">
            <div className="font-medium line-clamp-2">{m.title}</div>
            <div className="text-xs text-neutral-400">{m.creator} · {m.platform}</div>
            <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs pt-1">
              <Stat label="Views" value={fmt(m.views)} />
              <Stat label="Likes" value={fmt(m.likes)} />
              <Stat label="Comments" value={fmt(m.comments)} />
              <Stat label="Engagement" value={`${m.engagement_rate.toFixed(2)}%`} highlight />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div>
      <div className="text-neutral-500">{label}</div>
      <div className={highlight ? 'text-emerald-400 font-medium' : 'text-neutral-200'}>{value}</div>
    </div>
  );
}
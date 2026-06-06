export interface VideoMetadata {
  platform: 'youtube' | 'instagram';
  video_id: string;
  url: string;
  title: string;
  creator: string;
  creator_followers: number | null;
  upload_date: string | null;
  duration_seconds: number;
  views: number;
  likes: number;
  comments: number;
  engagement_rate: number;
  hashtags: string[];
  thumbnail_url: string | null;
}

export interface IngestedVideo {
  metadata: VideoMetadata;
  transcript: Array<{ text: string; start: number; duration: number }>;
  transcript_source: string;
}

export interface IngestResponse {
  video: IngestedVideo;
  chunks_indexed: number;
}

export interface Citation {
  source_index: number;
  video_id: string;
  platform: string;
  creator: string;
  position: number;
  start_time: number;
  end_time: number;
  text: string;
  score: number;
}

export type SSEEvent =
  | { type: 'citations'; chunks: Citation[] }
  | { type: 'token'; text: string }
  | { type: 'done'; length: number }
  | { type: 'error'; message: string };

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
}
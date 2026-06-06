import { useState } from 'react';

const KEY = 'rcr-session-id';

export function useSession(): string {
  const [sessionId] = useState(() => {
    const existing = sessionStorage.getItem(KEY);
    if (existing) return existing;
    const fresh = crypto.randomUUID();
    sessionStorage.setItem(KEY, fresh);
    return fresh;
  });
  return sessionId;
}
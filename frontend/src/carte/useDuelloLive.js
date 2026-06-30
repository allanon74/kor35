import { useCallback, useEffect, useRef, useState } from 'react';

/**
 * WebSocket live per duello carte (fallback: nessun poll — il client può refetch su azione).
 */
export function useDuelloLive(duelloId, onUpdate) {
  const wsRef = useRef(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!duelloId) return undefined;
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${wsProtocol}//${window.location.host}/ws/duello/${duelloId}/`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (data.type === 'duello_update' && data.payload) {
          onUpdate?.(data.payload);
        }
      } catch {
        /* noop */
      }
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [duelloId, onUpdate]);

  return { connected };
}

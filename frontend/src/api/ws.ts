import type { WsEvent } from '../types';

export function connectWS(onEvent: (e: WsEvent) => void): () => void {
  let ws: WebSocket | null = null;
  let closed = false;
  let retry = 0;

  const open = () => {
    ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`);
    ws.onmessage = (m) => {
      try {
        onEvent(JSON.parse(m.data));
      } catch {
        /* ignore */
      }
    };
    ws.onclose = () => {
      if (!closed) {
        retry = Math.min(retry + 1, 10);
        setTimeout(open, 1000 * retry);
      }
    };
    ws.onopen = () => {
      retry = 0;
    };
  };
  open();
  return () => {
    closed = true;
    ws?.close();
  };
}

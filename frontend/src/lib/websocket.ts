const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws";

export function createWebSocket(
  onMessage: (data: any) => void,
  onClose?: () => void,
): WebSocket {
  const ws = new WebSocket(WS_URL);

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch (e) {
      console.error("WebSocket parse error:", e);
    }
  };

  ws.onerror = (e) => console.error("WebSocket error:", e);
  ws.onclose = () => onClose?.();

  return ws;
}

export function subscribeTicker(ws: WebSocket, ticker: string) {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ subscribe: ticker }));
  }
}

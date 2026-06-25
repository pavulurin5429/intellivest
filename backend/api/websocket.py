"""
WebSocket endpoint for live dashboard updates.
Pushes analysis status updates to connected clients (sub-3s refresh).
"""

from __future__ import annotations
import asyncio
import json
from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger
from .routes.analysis import _cache


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        dead = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead.append(connection)
        for conn in dead:
            self.active_connections.remove(conn)


manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket handler. Streams analysis cache updates every 2 seconds.
    Client can send: {"subscribe": "AAPL"} to watch a specific ticker.
    """
    await manager.connect(websocket)
    subscribed_tickers: set[str] = set()

    try:
        async def send_updates():
            while True:
                await asyncio.sleep(2)
                if subscribed_tickers:
                    updates = {
                        ticker: _cache.get(ticker, {"status": "not_started"})
                        for ticker in subscribed_tickers
                    }
                    await websocket.send_json({"type": "update", "data": updates})
                else:
                    # Broadcast all active analyses
                    await websocket.send_json({"type": "update", "data": _cache})

        update_task = asyncio.create_task(send_updates())

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            if "subscribe" in message:
                ticker = message["subscribe"].upper()
                subscribed_tickers.add(ticker)
                await websocket.send_json({"type": "subscribed", "ticker": ticker})
            elif "unsubscribe" in message:
                subscribed_tickers.discard(message["unsubscribe"].upper())

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        update_task.cancel()
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

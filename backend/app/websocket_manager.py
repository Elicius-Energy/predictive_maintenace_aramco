"""
WebSocket manager for broadcasting real-time data to clients.
"""
import logging
import json
import asyncio
from typing import List, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from app.models import WSMessage
from app.config import get_runtime_settings

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages active WebSocket connections."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()
        self.error_counts: Dict[WebSocket, int] = {}

    async def connect(self, websocket: WebSocket):
        """Accept a new connection."""
        settings = get_runtime_settings()
        
        async with self._lock:
            if len(self.active_connections) >= settings.MAX_WS_CONNECTIONS:
                logger.warning(f"WebSocket connection rejected: Max connections ({settings.MAX_WS_CONNECTIONS}) reached")
                await websocket.close(code=1008, reason="Max connections reached")
                return False
                
            await websocket.accept()
            self.active_connections.append(websocket)
            self.error_counts[websocket] = 0
            logger.info(f"New client connected. Total: {len(self.active_connections)}")
            return True

    async def disconnect(self, websocket: WebSocket):
        """Handle disconnection."""
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
            self.error_counts.pop(websocket, None)
            
            # Make sure it's actually closed
            if websocket.client_state != WebSocketState.DISCONNECTED:
                try:
                    await websocket.close()
                except Exception:
                    pass
            logger.info(f"Client disconnected. Total: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send a message to a single client."""
        try:
            await websocket.send_text(message)
            self.error_counts[websocket] = 0
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            await self._handle_send_error(websocket)

    async def broadcast(self, message: WSMessage):
        """Broadcast a message to all connected clients concurrently."""
        if not self.active_connections:
            return
            
        message_json = message.model_dump_json()
        
        # Snapshot of connections to avoid issues during iteration
        async with self._lock:
            connections_to_notify = list(self.active_connections)
            
        if not connections_to_notify:
            return
            
        # Broadcast concurrently using asyncio.gather
        tasks = [self._safe_send(conn, message_json) for conn in connections_to_notify]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_send(self, websocket: WebSocket, message_json: str):
        """Helper to send a message and handle errors."""
        try:
            await websocket.send_text(message_json)
            self.error_counts[websocket] = 0 # reset on success
        except Exception as e:
            await self._handle_send_error(websocket)
            
    async def _handle_send_error(self, websocket: WebSocket):
        """Increment error count and disconnect if threshold reached."""
        count = self.error_counts.get(websocket, 0) + 1
        self.error_counts[websocket] = count
        if count >= 5:
            logger.warning("Disconnecting client due to repeated errors")
            await self.disconnect(websocket)
            
    def get_connection_count(self) -> int:
        return len(self.active_connections)

# Singleton
ws_manager = ConnectionManager()

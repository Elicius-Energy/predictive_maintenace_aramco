"""
WebSocket manager for broadcasting real-time data to clients.
"""
import logging
import json
from typing import List, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect
from app.models import WSMessage

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages active WebSocket connections."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept a new connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"New client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Handle disconnection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"Client disconnected. Total: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send a message to a single client."""
        await websocket.send_text(message)

    async def broadcast(self, message: WSMessage):
        """Broadcast a message to all connected clients."""
        if not self.active_connections:
            return
            
        message_json = message.model_dump_json()
        
        # Snapshot of connections to avoid issues during iteration
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                self.disconnect(connection)

# Singleton
ws_manager = ConnectionManager()

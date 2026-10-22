"""
WebSocket endpoints for real-time streaming.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.websocket_manager import ws_manager
from app.auth import verify_token
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ws"])

@router.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for real-time data."""
    # 1. Authenticate via subprotocol instead of query string
    token = None
    if "sec-websocket-protocol" in websocket.headers:
        protocols = websocket.headers.get("sec-websocket-protocol", "").split(",")
        if len(protocols) >= 2 and protocols[0].strip() == "access_token":
            token = protocols[1].strip()
            
    # Accept the subprotocol explicitly if token is provided
    # The actual accept will happen in ws_manager.connect
    subprotocol = "access_token" if token else None
    
    # 1. Authenticate via token before fully accepting
    if not token or token == "undefined" or token == "null":
        # In dev mode we might allow it without token, but check config
        from app.config import get_runtime_settings
        settings = get_runtime_settings()
        if settings.ADMIN_PASSWORD_HASH:
            # Prod mode: require token
            logger.warning("WebSocket connection rejected: No token provided")
            await websocket.close(code=1008, reason="Authentication required")
            return
    else:
        try:
            # Check token validity
            verify_token(token)
        except Exception as e:
            logger.warning(f"WebSocket connection rejected: Invalid token - {e}")
            await websocket.close(code=1008, reason="Invalid token")
            return

    # 2. Connect via manager (handles max connections check)
    connected = await ws_manager.connect(websocket, subprotocol=subprotocol)
    if not connected:
        return # Manager already closed it with 1008
        
    try:
        while True:
            # Keep connection open. We can also receive commands here.
            data = await websocket.receive_text()
            # Handle client-to-server messages if needed
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Unexpected WebSocket error: {e}")
        await ws_manager.disconnect(websocket)

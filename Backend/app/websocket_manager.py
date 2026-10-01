from typing import List
from fastapi import WebSocket
import json
import logging

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        if websocket not in self.active_connections:
            self.active_connections.append(websocket)
        logger.info(f"WebSocket connected to /ws. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket disconnected from /ws. Total clients: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        msg_str = json.dumps(message)
        stale = []
        for connection in list(self.active_connections):
            try:
                await connection.send_text(msg_str)
            except Exception as e:
                logger.error(f"Error broadcasting to /ws client: {e}")
                stale.append(connection)

        for s in stale:
            if s in self.active_connections:
                self.active_connections.remove(s)

        # Also forward to hardware_events clients if applicable
        try:
            from .hardware.usb.usb_events import hardware_events
            for ws in list(hardware_events._clients):
                if ws not in self.active_connections:
                    try:
                        await ws.send_text(msg_str)
                    except Exception:
                        pass
        except Exception:
            pass


ws_manager = WebSocketManager()

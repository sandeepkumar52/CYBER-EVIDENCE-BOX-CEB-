import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Set
from fastapi import WebSocket

logger = logging.getLogger("ceb.hardware.events")


class HardwareEventDispatcher:
    def __init__(self):
        self._clients: Set[WebSocket] = set()
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._clients.add(websocket)
        logger.info(f"WebSocket client connected. Active clients: {len(self._clients)}")

    def disconnect(self, websocket: WebSocket) -> None:
        self._clients.discard(websocket)
        logger.info(f"WebSocket client disconnected. Active clients: {len(self._clients)}")

    async def broadcast(self, event_type: str, data: Dict[str, Any]) -> None:
        payload = {
            "event": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **data,
        }
        message = json.dumps(payload)

        stale_clients = set()
        for ws in list(self._clients):
            try:
                await ws.send_text(message)
            except Exception as e:
                logger.debug(f"Error sending to WebSocket client: {e}")
                stale_clients.add(ws)

        for ws in stale_clients:
            self._clients.discard(ws)

        # Also forward to general /ws clients
        try:
            from ...websocket_manager import ws_manager
            for ws in list(ws_manager.active_connections):
                if ws not in self._clients:
                    try:
                        await ws.send_text(message)
                    except Exception:
                        pass
        except Exception:
            pass

    def dispatch_from_thread(self, event_type: str, data: Dict[str, Any]) -> None:
        """Thread-safe event broadcast from background serial or detection threads."""
        try:
            loop = self._loop
            if loop and loop.is_running():
                asyncio.run_coroutine_threadsafe(self.broadcast(event_type, data), loop)
            else:
                # Try getting current running loop
                try:
                    curr_loop = asyncio.get_running_loop()
                    asyncio.run_coroutine_threadsafe(self.broadcast(event_type, data), curr_loop)
                except RuntimeError:
                    pass
        except Exception as e:
            logger.debug(f"Failed to dispatch hardware event '{event_type}': {e}")


# Global event dispatcher
hardware_events = HardwareEventDispatcher()

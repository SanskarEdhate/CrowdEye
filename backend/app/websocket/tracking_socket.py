import json
import logging
from typing import Dict, Set, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger("crowdeye.websocket.tracking")

router = APIRouter(tags=["Tracking WebSocket"])


class TrackingConnectionManager:
    """
    Manages active WebSocket connections for live DeepSORT tracking telemetry streams.
    """

    def __init__(self):
        # job_id -> set of active WebSockets
        self.job_connections: Dict[str, Set[WebSocket]] = {}
        self.broadcast_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket, job_id: Optional[str] = None):
        await websocket.accept()
        self.broadcast_connections.add(websocket)
        if job_id:
            if job_id not in self.job_connections:
                self.job_connections[job_id] = set()
            self.job_connections[job_id].add(websocket)
        logger.info(f"WebSocket client connected (job_id={job_id}). Total: {len(self.broadcast_connections)}")

    def disconnect(self, websocket: WebSocket, job_id: Optional[str] = None):
        self.broadcast_connections.discard(websocket)
        if job_id and job_id in self.job_connections:
            self.job_connections[job_id].discard(websocket)
            if not self.job_connections[job_id]:
                self.job_connections.pop(job_id, None)
        logger.info(f"WebSocket client disconnected (job_id={job_id}).")

    async def broadcast_track(self, job_id: str, track_payload: Dict[str, Any]):
        """
        Broadcasts an individual track or frame telemetry dictionary.
        Format example:
        {
            "person_id": 25,
            "x": 120,
            "y": 300,
            "direction": "LEFT",
            "speed": 40.5
        }
        """
        message = json.dumps(track_payload)
        targets = set(self.broadcast_connections)
        if job_id in self.job_connections:
            targets.update(self.job_connections[job_id])

        disconnected = []
        for ws in targets:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)

        for ws in disconnected:
            self.disconnect(ws, job_id)

    def sync_broadcast_track(self, job_id: str, track_payload: Dict[str, Any]):
        """
        Thread-safe synchronous bridge for background worker tasks.
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(self.broadcast_track(job_id, track_payload), loop)
            else:
                loop.run_until_complete(self.broadcast_track(job_id, track_payload))
        except Exception:
            pass

    async def broadcast_risk(self, camera_id: str, risk_payload: Dict[str, Any]):
        """
        Broadcasts real-time crowd risk alerts & early warnings.
        Payload format:
        {
            "type": "risk_update",
            "camera_id": str,
            "zone": "A",
            "risk_score": 85,
            "risk_level": "CRITICAL",
            "reasons": [...]
        }
        """
        message = json.dumps(risk_payload)
        targets = set(self.broadcast_connections)
        disconnected = []
        for ws in targets:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)

        for ws in disconnected:
            self.disconnect(ws)

    def sync_broadcast_risk(self, camera_id: str, risk_payload: Dict[str, Any]):
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(self.broadcast_risk(camera_id, risk_payload), loop)
            else:
                loop.run_until_complete(self.broadcast_risk(camera_id, risk_payload))
        except Exception:
            pass


tracking_manager = TrackingConnectionManager()



@router.websocket("/ws/tracking")
async def websocket_tracking_global(websocket: WebSocket):
    """
    Global WebSocket stream for live tracking telemetry across all active jobs.
    """
    await tracking_manager.connect(websocket)
    try:
        while True:
            # Keep connection open / listen for client pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        tracking_manager.disconnect(websocket)
    except Exception:
        tracking_manager.disconnect(websocket)


@router.websocket("/ws/tracking/{job_id}")
async def websocket_tracking_job(websocket: WebSocket, job_id: str):
    """
    Job-specific WebSocket stream broadcasting DeepSORT tracks for a given job_id.
    """
    await tracking_manager.connect(websocket, job_id=job_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        tracking_manager.disconnect(websocket, job_id=job_id)
    except Exception:
        tracking_manager.disconnect(websocket, job_id=job_id)

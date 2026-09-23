import json
import logging
import asyncio
from typing import Dict, Set, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger("crowdeye.websocket.realtime")

router = APIRouter(tags=["Realtime WebSocket"])


class RealtimeConnectionManager:
    """
    Manages active WebSocket connections with topic-based subscriptions:
    - camera:{camera_id}
    - zone:{zone_id}
    - alerts
    - global broadcast
    """

    def __init__(self):
        # topic -> set of active WebSockets
        self.topic_subscribers: Dict[str, Set[WebSocket]] = {
            "alerts": set(),
            "all": set()
        }
        self.all_connections: Set[WebSocket] = set()
        self.job_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, initial_topics: Optional[list] = None):
        await websocket.accept()
        self.all_connections.add(websocket)
        self.topic_subscribers["all"].add(websocket)
        
        # Subscribe to initial topics if specified
        if initial_topics:
            for topic in initial_topics:
                self.subscribe(websocket, topic)
        else:
            # Default subscribe to alerts and global events
            self.subscribe(websocket, "alerts")

        logger.info(f"Realtime WebSocket client connected. Active: {len(self.all_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.all_connections.discard(websocket)
        for topic, subs in list(self.topic_subscribers.items()):
            subs.discard(websocket)
            if not subs and topic not in ("alerts", "all"):
                self.topic_subscribers.pop(topic, None)

        for job_id, subs in list(self.job_connections.items()):
            subs.discard(websocket)
            if not subs:
                self.job_connections.pop(job_id, None)

        logger.info("Realtime WebSocket client disconnected.")

    def subscribe(self, websocket: WebSocket, topic: str):
        if topic not in self.topic_subscribers:
            self.topic_subscribers[topic] = set()
        self.topic_subscribers[topic].add(websocket)
        logger.debug(f"Client subscribed to topic '{topic}'. Total subs: {len(self.topic_subscribers[topic])}")

    def unsubscribe(self, websocket: WebSocket, topic: str):
        if topic in self.topic_subscribers:
            self.topic_subscribers[topic].discard(websocket)

    async def broadcast_event(self, event_name: str, payload: Dict[str, Any], topic: Optional[str] = None):
        """
        Broadcasts an event to subscribers of a topic (and global listeners).
        Standard schema:
        {
            "event": event_name,
            ...payload
        }
        """
        msg_dict = dict(payload)
        msg_dict["event"] = event_name
        message = json.dumps(msg_dict)

        recipients = set(self.all_connections)
        if topic and topic in self.topic_subscribers:
            recipients.update(self.topic_subscribers[topic])

        disconnected = []
        for ws in recipients:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)

        for ws in disconnected:
            self.disconnect(ws)

    def sync_broadcast_event(self, event_name: str, payload: Dict[str, Any], topic: Optional[str] = None):
        """
        Thread-safe synchronous bridge for background threads & synchronous route handlers.
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(self.broadcast_event(event_name, payload, topic), loop)
            else:
                loop.run_until_complete(self.broadcast_event(event_name, payload, topic))
        except Exception as e:
            logger.debug(f"sync_broadcast_event fallback exception: {e}")

    # Backwards-compatibility helpers for Phase 3 DeepSORT tracking
    async def broadcast_track(self, job_id: str, track_payload: Dict[str, Any]):
        track_payload["event"] = "track_update"
        message = json.dumps(track_payload)
        targets = set(self.all_connections)
        if job_id in self.job_connections:
            targets.update(self.job_connections[job_id])

        disconnected = []
        for ws in targets:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect(ws)

    def sync_broadcast_track(self, job_id: str, track_payload: Dict[str, Any]):
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(self.broadcast_track(job_id, track_payload), loop)
            else:
                loop.run_until_complete(self.broadcast_track(job_id, track_payload))
        except Exception:
            pass

    async def broadcast_risk(self, camera_id: str, risk_payload: Dict[str, Any]):
        topic = f"camera:{camera_id}" if camera_id else "alerts"
        await self.broadcast_event("risk_update", risk_payload, topic=topic)

    def sync_broadcast_risk(self, camera_id: str, risk_payload: Dict[str, Any]):
        topic = f"camera:{camera_id}" if camera_id else "alerts"
        self.sync_broadcast_event("risk_update", risk_payload, topic=topic)


realtime_manager = RealtimeConnectionManager()
# Alias for backwards compatibility with earlier phases
tracking_manager = realtime_manager


@router.websocket("/ws/realtime")
async def websocket_realtime_endpoint(websocket: WebSocket):
    """
    Main Realtime WebSocket endpoint for the Security Operator Dashboard.
    Supports topic subscriptions:
      camera:{camera_id}
      zone:{zone_id}
      alerts
    Receives events:
      risk_update, alert_created, alert_resolved, camera_status
    """
    await realtime_manager.connect(websocket)
    try:
        while True:
            raw_text = await websocket.receive_text()
            try:
                data = json.loads(raw_text)
                action = data.get("action")
                topic = data.get("topic")
                if action == "subscribe" and topic:
                    realtime_manager.subscribe(websocket, topic)
                    await websocket.send_text(json.dumps({"status": "subscribed", "topic": topic}))
                elif action == "unsubscribe" and topic:
                    realtime_manager.unsubscribe(websocket, topic)
                    await websocket.send_text(json.dumps({"status": "unsubscribed", "topic": topic}))
                elif action == "ping":
                    await websocket.send_text(json.dumps({"status": "pong"}))
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        realtime_manager.disconnect(websocket)
    except Exception:
        realtime_manager.disconnect(websocket)


@router.websocket("/ws/alerts")
async def websocket_alerts_endpoint(websocket: WebSocket):
    """
    Dedicated WebSocket stream for alert notifications only.
    """
    await realtime_manager.connect(websocket, initial_topics=["alerts"])
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        realtime_manager.disconnect(websocket)
    except Exception:
        realtime_manager.disconnect(websocket)


@router.websocket("/ws/tracking")
async def websocket_tracking_global(websocket: WebSocket):
    """
    Global WebSocket stream for live tracking telemetry across all active jobs.
    """
    await realtime_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        realtime_manager.disconnect(websocket)
    except Exception:
        realtime_manager.disconnect(websocket)


@router.websocket("/ws/tracking/{job_id}")
async def websocket_tracking_job(websocket: WebSocket, job_id: str):
    """
    Job-specific WebSocket stream broadcasting DeepSORT tracks for a given job_id.
    """
    await websocket.accept()
    realtime_manager.all_connections.add(websocket)
    if job_id not in realtime_manager.job_connections:
        realtime_manager.job_connections[job_id] = set()
    realtime_manager.job_connections[job_id].add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        realtime_manager.disconnect(websocket)
    except Exception:
        realtime_manager.disconnect(websocket)

"""
CrowdEye AI - Dedicated AI Inference Worker Package (Phase 7).
Decoupled from FastAPI HTTP Application Server.
"""
from ai_worker.inference import UnifiedInferenceEngine
from ai_worker.video_queue import video_queue
from ai_worker.worker import AIWorkerService

__all__ = ["UnifiedInferenceEngine", "video_queue", "AIWorkerService"]

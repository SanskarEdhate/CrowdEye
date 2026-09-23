"""CrowdEye AI - Detection Package"""
from .yolo_detector import YOLODetector
from .video_processor import process_video

__all__ = ["YOLODetector", "process_video"]

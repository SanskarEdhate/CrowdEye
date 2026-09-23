"""
CrowdEye AI - Local DeepSORT Tracking & Movement Viewer (Developer Tool)
Renders live bounding boxes, persistent person IDs, and directional arrows.
FOR LOCAL TESTING ONLY — NOT USED BY FASTAPI.
"""

import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.detection.yolo_detector import YOLODetector
from ai.tracking.deepsort_tracker import DeepSortTracker
from ai.tracking.track_history import TrackHistory
from ai.tracking.movement_analyzer import MovementAnalyzer


def run_tracking_viewer(video_source: str = "videos/input/test.mp4"):
    """
    Renders live video stream with DeepSORT tracking boxes, IDs, and movement arrows.
    """
    import cv2
    import numpy as np

    source = int(video_source) if video_source.isdigit() else video_source
    cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        print(f"[Error] Cannot open video source: {video_source}")
        return

    detector = YOLODetector()
    tracker = DeepSortTracker()
    history = TrackHistory(max_history_seconds=10.0)

    # Color palette based on ID
    np.random.seed(42)
    colors = np.random.randint(64, 255, size=(1000, 3)).tolist()

    print("\n[CrowdEye AI] Starting DeepSORT Tracking & Movement Viewer...")
    print("Press 'q' or 'ESC' to exit.\n")

    frame_idx = 0
    fps = 0.0
    prev_time = time.time()

    direction_symbols = {
        "RIGHT": "->",
        "LEFT": "<-",
        "UP": "^",
        "DOWN": "v",
        "UP-RIGHT": "^>",
        "UP-LEFT": "<^",
        "DOWN-RIGHT": "v>",
        "DOWN-LEFT": "<v",
        "STATIONARY": "."
    }

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[Info] End of video reached.")
            break

        now = time.time()
        fps = 0.9 * fps + 0.1 * (1.0 / max(now - prev_time, 0.0001))
        prev_time = now

        # 1. Run YOLOv8 detection
        yolo_result = detector.detect_people(frame)
        persons = yolo_result.get("persons", [])

        # 2. Update DeepSORT tracks
        tracks = tracker.update(persons, frame)

        # 3. Update history and draw tracking overlays
        for t in tracks:
            pid = t["person_id"]
            x1, y1, x2, y2 = t["bbox"]
            cx = (x1 + x2) / 2.0
            cy = (y1 + y2) / 2.0

            # Record point in history
            history.add_point(pid, cx, cy, timestamp=now)

            # Analyze recent movement
            recent = history.get_recent_positions(pid, window_seconds=1.5)
            motion = MovementAnalyzer.analyze_motion(pid, recent)
            direction = motion["direction"]
            speed = motion["speed"]

            color = tuple(colors[pid % len(colors)])

            # Draw bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            # Draw trajectory path trail
            pts = [(int(p[0]), int(p[1])) for p in recent]
            for i in range(1, len(pts)):
                cv2.line(frame, pts[i - 1], pts[i], color, 2)

            # Tag label: Person ID + Direction + Speed
            arrow = direction_symbols.get(direction, "")
            label = f"ID {pid} {arrow} {int(speed)}px/s"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(frame, (x1, max(y1 - 22, 0)), (x1 + tw + 6, max(y1, 22)), (15, 21, 35), -1)
            cv2.putText(frame, label, (x1 + 3, max(y1 - 6, 16)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

        # Draw HUD Box
        hud = frame.copy()
        cv2.rectangle(hud, (10, 10), (360, 95), (10, 13, 20), -1)
        cv2.addWeighted(hud, 0.75, frame, 0.25, 0, frame)

        cv2.putText(frame, "CrowdEye AI - DeepSORT Tracking", (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (56, 189, 248), 2)
        cv2.putText(frame, f"Active Tracks: {len(tracks)}", (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (16, 185, 129), 2)
        cv2.putText(frame, f"Tracking FPS: {fps:.1f}", (20, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (148, 163, 184), 1)

        cv2.imshow("CrowdEye AI - DeepSORT Movement Viewer", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q") or key == 27:
            break

        frame_idx += 1

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "videos/input/test.mp4"
    run_tracking_viewer(target)

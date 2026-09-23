"""
CrowdEye AI - Local Demo Viewer (Developer Tool)
Displays real-time bounding boxes, live headcount, and FPS using cv2.imshow().
FOR LOCAL TESTING ONLY — NOT USED BY FASTAPI BACKEND.
"""

import sys
import time
from pathlib import Path
from yolo_detector import YOLODetector


def run_demo(video_source: str = "0"):
    """
    Runs real-time OpenCV viewer on a video file or webcam.

    Args:
        video_source: Path to an mp4/avi video file, or '0' for webcam.
    """
    import cv2

    source = int(video_source) if video_source.isdigit() else video_source
    cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        print(f"[Error] Unable to open video source: {video_source}")
        return

    detector = YOLODetector()
    print("\n[CrowdEye AI] Starting Local Demo Viewer...")
    print("Press 'q' or 'ESC' in the video window to exit.\n")

    prev_time = time.time()
    fps = 0.0

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[Info] End of video stream reached.")
            break

        # Calculate FPS
        current_time = time.time()
        fps = 0.9 * fps + 0.1 * (1.0 / max(current_time - prev_time, 0.0001))
        prev_time = current_time

        # Run Person Detection
        results = detector.detect_people(frame)
        count = results["count"]

        # Draw Bounding Boxes
        for person in results["persons"]:
            x1, y1, x2, y2 = person["x1"], person["y1"], person["x2"], person["y2"]
            conf = person["confidence"]

            # Cyan bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), (248, 189, 56), 2)

            # Label banner
            label = f"Person: {int(conf * 100)}%"
            (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(frame, (x1, max(y1 - 20, 0)), (x1 + w + 6, max(y1, 20)), (20, 28, 46), -1)
            cv2.putText(
                frame,
                label,
                (x1 + 3, max(y1 - 5, 15)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (255, 255, 255),
                1,
                cv2.LINE_AA
            )

        # Header HUD
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, 10), (320, 95), (10, 13, 20), -1)
        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

        # Status text
        cv2.putText(frame, "CrowdEye AI - YOLOv8", (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (56, 189, 248), 2)
        cv2.putText(frame, f"Detected People: {count}", (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (16, 185, 129), 2)
        cv2.putText(frame, f"Inference FPS: {fps:.1f}", (20, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (148, 163, 184), 1)

        # Show frame
        cv2.imshow("CrowdEye AI - YOLOv8 Person Detection Demo", frame)

        # Exit on key press
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q") or key == 27:
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "videos/input/test.mp4"
    run_demo(target)

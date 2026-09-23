import cv2
import numpy as np
from typing import List, Tuple, Optional, Union


class PerspectiveTransformer:
    """
    Performs camera perspective correction using 2D projective homography.

    NOTE ON CAMERA CALIBRATION:
    Accurate physical density (people / m^2) requires extrinsic camera calibration
    (camera elevation angle, focal length, sensor dimensions, and ground plane markers).
    Without physical surveying, this module provides 2D projective rectification
    from an angled trapezoidal camera viewport to a normalized bird's-eye ground plane.
    """
    def __init__(
        self,
        src_points: Optional[List[List[float]]] = None,
        dst_points: Optional[List[List[float]]] = None,
        frame_width: int = 640,
        frame_height: int = 480
    ):
        self.frame_width = frame_width
        self.frame_height = frame_height

        if src_points and dst_points and len(src_points) == 4 and len(dst_points) == 4:
            src = np.array(src_points, dtype=np.float32)
            dst = np.array(dst_points, dtype=np.float32)
            self.homography_matrix, _ = cv2.findHomography(src, dst)
        else:
            # Calibrated default for standard tilted overhead CCTV angle:
            # Maps foreground wider trapezoid and background narrower trapezoid
            # into a normalized rectangular top-down perspective.
            src = np.array([
                [frame_width * 0.15, frame_height * 0.20],  # Top-Left (distant)
                [frame_width * 0.85, frame_height * 0.20],  # Top-Right (distant)
                [frame_width * 0.95, frame_height * 0.95],  # Bottom-Right (near)
                [frame_width * 0.05, frame_height * 0.95]   # Bottom-Left (near)
            ], dtype=np.float32)

            dst = np.array([
                [0, 0],
                [frame_width, 0],
                [frame_width, frame_height],
                [0, frame_height]
            ], dtype=np.float32)

            self.homography_matrix = cv2.getPerspectiveTransform(src, dst)

    def transform_point(self, x: float, y: float) -> Tuple[float, float]:
        """
        Transforms an image point (x, y) into its perspective-corrected ground coordinate.
        """
        pt = np.array([[[float(x), float(y)]]], dtype=np.float32)
        transformed = cv2.perspectiveTransform(pt, self.homography_matrix)
        tx = float(transformed[0][0][0])
        ty = float(transformed[0][0][1])
        return tx, ty

    def transform_points(self, points: List[Union[Tuple[float, float], List[float]]]) -> List[Tuple[float, float]]:
        """
        Batch transforms multiple (x, y) coordinates.
        """
        if not points:
            return []

        pts = np.array([points], dtype=np.float32)
        transformed = cv2.perspectiveTransform(pts, self.homography_matrix)
        return [(float(pt[0]), float(pt[1])) for pt in transformed[0]]

    def warp_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Warps an entire image frame into top-down perspective (useful for visualization).
        """
        return cv2.warpPerspective(frame, self.homography_matrix, (self.frame_width, self.frame_height))

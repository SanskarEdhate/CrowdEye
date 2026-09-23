import cv2
import numpy as np
from typing import List, Dict, Any, Union, Tuple, Optional


class HeatmapGenerator:
    """
    Dynamically generates 2D Gaussian crowd density distributions.
    Produces lightweight JSON-serializable intensity coordinate arrays
    for client-side canvas/leaflet rendering WITHOUT persisting heavy image files.
    """
    def __init__(
        self,
        grid_width: int = 640,
        grid_height: int = 480,
        gaussian_ksize: int = 45,
        gaussian_sigma: float = 15.0,
        downsample_factor: int = 16
    ):
        self.grid_width = grid_width
        self.grid_height = grid_height
        self.ksize = gaussian_ksize if gaussian_ksize % 2 == 1 else gaussian_ksize + 1
        self.sigma = gaussian_sigma
        self.downsample = max(1, downsample_factor)

    def generate_density_matrix(self, persons: List[Union[Dict[str, Any], Tuple[float, float], List[float]]]) -> np.ndarray:
        """
        Creates a 2D float32 Gaussian density map where each person adds a kernel.
        """
        density_map = np.zeros((self.grid_height, self.grid_width), dtype=np.float32)

        for p in persons:
            if isinstance(p, dict):
                if "centroid" in p:
                    x, y = p["centroid"][0], p["centroid"][1]
                elif "x" in p and "y" in p:
                    x, y = p["x"], p["y"]
                elif "bbox" in p:
                    b = p["bbox"]
                    x = b[0] + b[2] / 2.0
                    y = b[1] + b[3] / 2.0
                else:
                    continue
            elif isinstance(p, (list, tuple)) and len(p) >= 2:
                x, y = p[0], p[1]
            else:
                continue

            ix = int(round(x))
            iy = int(round(y))

            if 0 <= ix < self.grid_width and 0 <= iy < self.grid_height:
                density_map[iy, ix] += 1.0

        # Apply 2D Gaussian filter to diffuse person points into crowd clouds
        if np.any(density_map > 0):
            density_map = cv2.GaussianBlur(
                density_map,
                (self.ksize, self.ksize),
                sigmaX=self.sigma,
                sigmaY=self.sigma
            )
            # Normalize to 0.0 - 1.0
            max_val = np.max(density_map)
            if max_val > 0:
                density_map = density_map / max_val

        return density_map

    def generate_heatmap_points(
        self,
        persons: List[Union[Dict[str, Any], Tuple[float, float], List[float]]],
        min_intensity: float = 0.05
    ) -> List[Dict[str, Any]]:
        """
        Returns downsampled [{ "x": int, "y": int, "intensity": float }] list
        suitable for low-latency JSON transmission and frontend canvas rendering.
        """
        matrix = self.generate_density_matrix(persons)
        points: List[Dict[str, Any]] = []

        step = self.downsample
        for y in range(0, self.grid_height, step):
            for x in range(0, self.grid_width, step):
                # Sample neighborhood intensity
                val = float(matrix[y, x])
                if val >= min_intensity:
                    points.append({
                        "x": x,
                        "y": y,
                        "intensity": round(val, 3)
                    })

        return points

    def render_overlay(self, frame: np.ndarray, density_matrix: Optional[np.ndarray] = None, alpha: float = 0.5) -> np.ndarray:
        """
        Optional debugging helper: Renders a pseudo-color heatmap overlay onto a BGR frame.
        """
        if density_matrix is None or not np.any(density_matrix > 0):
            return frame

        # Resize matrix to match frame if necessary
        fh, fw = frame.shape[:2]
        if (density_matrix.shape[0], density_matrix.shape[1]) != (fh, fw):
            density_resized = cv2.resize(density_matrix, (fw, fh))
        else:
            density_resized = density_matrix

        # Convert to 8-bit image
        norm_map = np.uint8(255 * np.clip(density_resized, 0, 1))
        colored_map = cv2.applyColorMap(norm_map, cv2.COLORMAP_JET)

        # Blend with original frame
        mask = norm_map > 15
        overlay = frame.copy()
        overlay[mask] = cv2.addWeighted(frame[mask], 1.0 - alpha, colored_map[mask], alpha, 0)
        return overlay

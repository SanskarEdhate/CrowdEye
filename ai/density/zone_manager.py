import cv2
import numpy as np
from typing import List, Dict, Any, Optional, Tuple


class Zone:
    """
    Represents a monitored spatial partition within a camera frame.
    """
    def __init__(
        self,
        name: str,
        capacity: int,
        coordinates: List[List[float]],
        color: Tuple[int, int, int] = (0, 255, 255)
    ):
        self.name = name
        self.capacity = max(1, capacity)
        self.coordinates = coordinates
        self.color = color

        # Polygon representation for point-in-polygon test
        if len(coordinates) == 2:
            # Bounding box format: [[x1, y1], [x2, y2]]
            x1, y1 = coordinates[0]
            x2, y2 = coordinates[1]
            self.polygon = np.array([
                [x1, y1],
                [x2, y1],
                [x2, y2],
                [x1, y2]
            ], dtype=np.int32)
        else:
            self.polygon = np.array(coordinates, dtype=np.int32)

    def contains_point(self, x: float, y: float) -> bool:
        """
        Tests if point (x, y) resides inside or on the boundary of this zone.
        """
        # pointPolygonTest returns >= 0 if inside or on edge
        return cv2.pointPolygonTest(self.polygon, (float(x), float(y)), False) >= 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "zone": self.name,
            "capacity": self.capacity,
            "coordinates": self.coordinates
        }


class ZoneManager:
    """
    Manages multiple spatial zones for a camera view.
    Defaults to a 2x3 venue grid (A, B, C, D, E, F) if no custom zones are provided.
    """
    def __init__(self, frame_width: int = 640, frame_height: int = 480, zones: Optional[List[Zone]] = None):
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.zones: List[Zone] = []

        if zones:
            for z in zones:
                self.add_zone(z)
        else:
            self._init_default_grid(frame_width, frame_height)

    def _init_default_grid(self, width: int, height: int):
        """
        Initializes default 2x3 grid:
        +-----------+-----------+-----------+
        |  Zone A   |  Zone B   |  Zone C   |
        +-----------+-----------+-----------+
        |  Zone D   |  Zone E   |  Zone F   |
        +-----------+-----------+-----------+
        """
        w3 = width / 3.0
        h2 = height / 2.0

        grid_specs = [
            ("A", 150, [[0, 0], [w3, h2]]),
            ("B", 200, [[w3, 0], [2 * w3, h2]]),
            ("C", 150, [[2 * w3, 0], [width, h2]]),
            ("D", 150, [[0, h2], [w3, height]]),
            ("E", 200, [[w3, h2], [2 * w3, height]]),
            ("F", 150, [[2 * w3, h2], [width, height]]),
        ]

        self.zones = [Zone(name=name, capacity=cap, coordinates=coords) for name, cap, coords in grid_specs]

    def add_zone(self, zone: Zone):
        self.zones.append(zone)

    def assign_to_zone(self, x: float, y: float) -> Optional[str]:
        """
        Maps a 2D coordinate to its containing zone name.
        """
        for zone in self.zones:
            if zone.contains_point(x, y):
                return zone.name
        return None

    def get_zone(self, name: str) -> Optional[Zone]:
        for zone in self.zones:
            if zone.name == name:
                return zone
        return None

    def count_people_per_zone(self, persons: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Computes people count per zone from a list of tracked persons.
        Each person dict is expected to have 'x' and 'y' (or 'centroid': [x, y]).
        """
        counts = {z.name: 0 for z in self.zones}

        for p in persons:
            if "centroid" in p:
                px, py = p["centroid"][0], p["centroid"][1]
            elif "x" in p and "y" in p:
                px, py = p["x"], p["y"]
            elif "bbox" in p:
                # [left, top, w, h]
                b = p["bbox"]
                px = b[0] + b[2] / 2.0
                py = b[1] + b[3] / 2.0
            else:
                continue

            zone_name = self.assign_to_zone(px, py)
            if zone_name in counts:
                counts[zone_name] += 1

        return counts

    def get_all_zones_summary(self) -> List[Dict[str, Any]]:
        return [z.to_dict() for z in self.zones]

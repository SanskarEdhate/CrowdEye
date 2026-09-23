import math
from typing import Dict, Any, List, Tuple, Optional


class MovementAnalyzer:
    """
    Computes pedestrian movement vectors, heading direction, and relative velocity
    in pixels/second from spatial-temporal track history.
    """

    @staticmethod
    def calculate_direction(
        p_prev: Tuple[float, float],
        p_curr: Tuple[float, float],
        min_displacement: float = 4.0
    ) -> str:
        """
        Determines the 8-way cardinal direction between two 2D points.
        Note: In image coordinates, y increases downward.
        """
        dx = p_curr[0] - p_prev[0]
        dy = p_curr[1] - p_prev[1]
        dist = math.hypot(dx, dy)

        if dist < min_displacement:
            return "STATIONARY"

        # Angle in degrees from -180 to +180
        deg = math.degrees(math.atan2(dy, dx))

        if -22.5 <= deg < 22.5:
            return "RIGHT"
        elif 22.5 <= deg < 67.5:
            return "DOWN-RIGHT"
        elif 67.5 <= deg < 112.5:
            return "DOWN"
        elif 112.5 <= deg < 157.5:
            return "DOWN-LEFT"
        elif deg >= 157.5 or deg < -157.5:
            return "LEFT"
        elif -157.5 <= deg < -112.5:
            return "UP-LEFT"
        elif -112.5 <= deg < -67.5:
            return "UP"
        elif -67.5 <= deg < -22.5:
            return "UP-RIGHT"

        return "STATIONARY"

    @staticmethod
    def calculate_speed(
        p_prev: Tuple[float, float],
        p_curr: Tuple[float, float],
        dt: float
    ) -> float:
        """
        Calculates speed strictly in pixels/second.
        Do NOT convert to meters/second as camera matrix calibration is not assumed.
        """
        if dt <= 0.0001:
            return 0.0

        dist = math.hypot(p_curr[0] - p_prev[0], p_curr[1] - p_prev[1])
        speed = dist / dt
        return round(speed, 1)

    @classmethod
    def analyze_motion(
        cls,
        person_id: int,
        history: List[Tuple[float, float, float]]
    ) -> Dict[str, Any]:
        """
        Analyzes motion across a temporal coordinate series [(x, y, time), ...].

        Returns:
            {
                "person_id": int,
                "direction": str,
                "speed": float,
                "unit": "pixels/sec"
            }
        """
        if not history or len(history) < 2:
            return {
                "person_id": person_id,
                "direction": "STATIONARY",
                "speed": 0.0,
                "unit": "pixels/sec"
            }

        # Compare earliest point in recent window to latest point for smoothed heading
        p_start = (history[0][0], history[0][1])
        p_end = (history[-1][0], history[-1][1])
        dt = history[-1][2] - history[0][2]

        direction = cls.calculate_direction(p_start, p_end, min_displacement=5.0)
        speed = cls.calculate_speed(p_start, p_end, dt)

        return {
            "person_id": person_id,
            "direction": direction,
            "speed": speed,
            "unit": "pixels/sec"
        }

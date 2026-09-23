import math
from typing import Dict, Any, List, Optional


class FeatureExtractor:
    """
    Extracts normalized crowd risk features (0 - 100) over a 10-second temporal analysis window.
    Features:
    1. Density Score (Normalized to 0 - 100)
    2. Crowd Growth Rate (% change over 10s, normalized to 0 - 100)
    3. Movement Activity (Relative speed scale, normalized to 0 - 100)
    4. Movement Chaos (Circular statistics dispersion, normalized to 0 - 100)
    """

    MAX_EXPECTED_SPEED_PX = 150.0  # Normalized relative speed benchmark

    DIRECTION_ANGLES = {
        "RIGHT": 0.0,
        "UP-RIGHT": math.pi / 4.0,
        "UP": math.pi / 2.0,
        "UP-LEFT": 3.0 * math.pi / 4.0,
        "LEFT": math.pi,
        "DOWN-LEFT": 5.0 * math.pi / 4.0,
        "DOWN": 3.0 * math.pi / 2.0,
        "DOWN-RIGHT": 7.0 * math.pi / 4.0
    }

    @classmethod
    def extract_density_norm(cls, people_count: int, zone_capacity: int) -> float:
        """
        Formula: density_norm = (people_count / zone_capacity) * 100
        Normalized range: [0.0, 100.0]
        """
        if zone_capacity <= 0:
            return 0.0
        val = (float(people_count) / float(zone_capacity)) * 100.0
        return round(max(0.0, min(100.0, val)), 2)

    @classmethod
    def extract_growth_norm(cls, current_people: int, previous_people: int) -> float:
        """
        Formula: growth_rate = ((current_people - previous_people) / previous_people) * 100
        Normalized range: [0.0, 100.0]
        """
        if previous_people <= 0:
            if current_people > 0:
                return min(100.0, current_people * 10.0)
            return 0.0

        rate = ((float(current_people) - float(previous_people)) / float(previous_people)) * 100.0
        return round(max(0.0, min(100.0, rate)), 2)

    @classmethod
    def extract_speed_norm(cls, current_speed_px: float, max_speed_px: Optional[float] = None) -> float:
        """
        Formula: speed_norm = (current_speed / maximum_expected_speed) * 100
        Normalized range: [0.0, 100.0]
        Strictly uses relative speed scale, prohibiting raw m/s assumptions.
        """
        max_speed = max_speed_px or cls.MAX_EXPECTED_SPEED_PX
        if max_speed <= 0:
            return 0.0
        val = (float(current_speed_px) / float(max_speed)) * 100.0
        return round(max(0.0, min(100.0, val)), 2)

    @classmethod
    def extract_chaos_norm(cls, directions: List[Any]) -> float:
        """
        Computes directional crowd chaos using Circular Statistics.
        DO NOT use standard variance np.var(angles).

        Formula:
        R = sqrt((sum(cos theta))^2 + (sum(sin theta))^2) / n
        Chaos = 1 - R
        chaos_norm = Chaos * 100
        Normalized range: [0.0, 100.0]
        """
        angles: List[float] = []

        for d in directions:
            if isinstance(d, (int, float)):
                angles.append(float(d))
            elif isinstance(d, str):
                cleaned = d.strip().upper()
                if cleaned in cls.DIRECTION_ANGLES:
                    angles.append(cls.DIRECTION_ANGLES[cleaned])
            elif isinstance(d, dict) and "direction" in d:
                cleaned = str(d["direction"]).strip().upper()
                if cleaned in cls.DIRECTION_ANGLES:
                    angles.append(cls.DIRECTION_ANGLES[cleaned])

        n = len(angles)
        if n <= 1:
            # Single or zero persons cannot exhibit multi-directional crowd turbulence
            return 0.0

        sum_cos = sum(math.cos(th) for th in angles)
        sum_sin = sum(math.sin(th) for th in angles)

        # Mean resultant vector length R (0 <= R <= 1)
        r = math.sqrt(sum_cos ** 2 + sum_sin ** 2) / float(n)
        r = max(0.0, min(1.0, r))

        chaos = 1.0 - r
        return round(chaos * 100.0, 2)

    @classmethod
    def extract_features(
        cls,
        people_count: int,
        zone_capacity: int,
        previous_people: int,
        current_speed: float,
        directions: List[Any]
    ) -> Dict[str, float]:
        """
        Extracts all 4 normalized features in a single call.
        """
        return {
            "density": cls.extract_density_norm(people_count, zone_capacity),
            "growth": cls.extract_growth_norm(people_count, previous_people),
            "speed": cls.extract_speed_norm(current_speed),
            "chaos": cls.extract_chaos_norm(directions)
        }

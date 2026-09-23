from typing import Dict, List, Any, Optional
from ai.density.zone_manager import ZoneManager


class DensityEstimator:
    """
    Calculates normalized density scores and assigns 4-tier density levels:
    - LOW: 0 - 40% (0.0 <= score < 0.40)
    - MEDIUM: 40 - 70% (0.40 <= score < 0.70)
    - HIGH: 70 - 90% (0.70 <= score < 0.90)
    - CRITICAL: 90%+ (score >= 0.90)
    """

    @staticmethod
    def classify_density_level(score: float) -> str:
        """
        Maps a normalized density score (0.0 to 1.0+) to a discrete density category.
        """
        if score < 0.40:
            return "LOW"
        elif score < 0.70:
            return "MEDIUM"
        elif score < 0.90:
            return "HIGH"
        else:
            return "CRITICAL"

    def __init__(self, zone_manager: Optional[ZoneManager] = None):
        self.zone_manager = zone_manager or ZoneManager()

    def estimate_zone_densities(
        self,
        persons: List[Dict[str, Any]],
        perspective_transformer: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Calculates people count, density score, and density level for each zone.
        Optionally applies perspective correction before zone assignment.
        """
        processed_persons = []
        for p in persons:
            # Extract point
            if "centroid" in p:
                px, py = p["centroid"][0], p["centroid"][1]
            elif "x" in p and "y" in p:
                px, py = p["x"], p["y"]
            elif "bbox" in p:
                b = p["bbox"]
                px = b[0] + b[2] / 2.0
                py = b[1] + b[3] / 2.0
            else:
                continue

            # Optional perspective correction
            if perspective_transformer:
                px, py = perspective_transformer.transform_point(px, py)

            processed_persons.append({
                "person_id": p.get("person_id"),
                "x": px,
                "y": py
            })

        counts = self.zone_manager.count_people_per_zone(processed_persons)
        results = []

        for zone in self.zone_manager.zones:
            count = counts.get(zone.name, 0)
            score = round(float(count) / float(zone.capacity), 3)
            level = self.classify_density_level(score)

            results.append({
                "zone": zone.name,
                "people_count": count,
                "capacity": zone.capacity,
                "density_score": score,
                "density_level": level
            })

        return results

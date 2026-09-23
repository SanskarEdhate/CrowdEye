from typing import Dict, Any, Tuple


class RiskEngine:
    """
    Deterministic, explainable crowd risk evaluation engine.
    Calculates safety risk index (0 - 100) from 4 normalized telemetry features:
    - 40% Density
    - 25% Speed
    - 20% Movement Chaos
    - 15% Growth Rate
    """

    WEIGHT_DENSITY = 0.40
    WEIGHT_SPEED = 0.25
    WEIGHT_CHAOS = 0.20
    WEIGHT_GROWTH = 0.15

    @classmethod
    def classify_risk_level(cls, score: float) -> str:
        """
        Maps risk score to 4-tier safety category:
        - 0 - 30: LOW
        - 31 - 60: MEDIUM
        - 61 - 80: HIGH
        - 81 - 100: CRITICAL
        """
        rounded = round(score)
        if rounded <= 30:
            return "LOW"
        elif rounded <= 60:
            return "MEDIUM"
        elif rounded <= 80:
            return "HIGH"
        else:
            return "CRITICAL"

    @classmethod
    def calculate_risk(
        cls,
        density: float,
        speed: float,
        chaos: float,
        growth: float
    ) -> Dict[str, Any]:
        """
        Computes the weighted risk score and assigns the risk level.

        Formula:
        Risk = 0.40*Density + 0.25*Speed + 0.20*Chaos + 0.15*Growth
        """
        raw_score = (
            cls.WEIGHT_DENSITY * float(density) +
            cls.WEIGHT_SPEED * float(speed) +
            cls.WEIGHT_CHAOS * float(chaos) +
            cls.WEIGHT_GROWTH * float(growth)
        )

        clamped_score = max(0.0, min(100.0, raw_score))
        final_score = int(round(clamped_score))
        level = cls.classify_risk_level(final_score)

        return {
            "risk_score": final_score,
            "risk_level": level,
            "components": {
                "density_contrib": round(cls.WEIGHT_DENSITY * float(density), 2),
                "speed_contrib": round(cls.WEIGHT_SPEED * float(speed), 2),
                "chaos_contrib": round(cls.WEIGHT_CHAOS * float(chaos), 2),
                "growth_contrib": round(cls.WEIGHT_GROWTH * float(growth), 2)
            }
        }

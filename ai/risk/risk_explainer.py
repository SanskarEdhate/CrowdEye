from typing import List, Dict, Any


class RiskExplainer:
    """
    Generates human-readable, transparent diagnostic explanations
    for calculated crowd safety risk evaluations.
    """

    @classmethod
    def explain_risk(
        cls,
        risk_score: int,
        features: Dict[str, float]
    ) -> List[str]:
        """
        Produces a prioritized list of explainable risk drivers.
        """
        density = features.get("density", 0.0)
        speed = features.get("speed", 0.0)
        chaos = features.get("chaos", 0.0)
        growth = features.get("growth", 0.0)

        reasons: List[str] = []

        # 1. Density Drivers
        if density >= 85.0:
            reasons.append("Critical crowd density exceeding safe zone capacity")
        elif density >= 70.0:
            reasons.append("High crowd density nearing zone capacity")
        elif density >= 50.0 and risk_score > 30:
            reasons.append("Moderate crowd accumulation")

        # 2. Growth Surge Drivers
        if growth >= 50.0:
            reasons.append("Severe crowd surge detected in last 10 seconds")
        elif growth >= 30.0:
            reasons.append("Rapid crowd increase over 10-second window")

        # 3. Directional Chaos Drivers
        if chaos >= 60.0:
            reasons.append("Chaotic multi-directional flow with counter-currents")
        elif chaos >= 40.0:
            reasons.append("Unstable movement pattern and directional conflict")

        # 4. Velocity / Bottleneck Drivers
        if speed >= 70.0:
            reasons.append("Abnormally high crowd movement velocity")
        elif speed < 15.0 and density >= 70.0:
            reasons.append("Stationary bottleneck / severe crowd compression forming")

        # Fallback if no specific high factor triggered but risk is elevated
        if not reasons:
            if risk_score > 60:
                reasons.append("Elevated composite crowd safety indicators")
            elif risk_score > 30:
                reasons.append("Moderate crowd activity requiring routine monitoring")
            else:
                reasons.append("Normal crowd flow within safety thresholds")

        return reasons

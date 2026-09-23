from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseRiskModel(ABC):
    """
    Abstract Base Class for crowd safety risk prediction models.
    Provides standard interface for current heuristic engine and future ML models:
    - Random Forest Regressor
    - XGBoost Gradient Booster
    - LSTM Spatiotemporal Recurrent Neural Network
    """

    @abstractmethod
    def predict(self, features: Dict[str, float]) -> float:
        """
        Takes normalized feature vector { "density": float, "speed": float, "chaos": float, "growth": float }
        and returns a predicted risk score (0.0 - 100.0).
        """
        pass


class HeuristicRiskModel(BaseRiskModel):
    """
    Phase 5 Default Model: Explainable deterministic weighted formulation.
    Risk = 0.40*Density + 0.25*Speed + 0.20*Chaos + 0.15*Growth
    """

    def predict(self, features: Dict[str, float]) -> float:
        d = float(features.get("density", 0.0))
        s = float(features.get("speed", 0.0))
        c = float(features.get("chaos", 0.0))
        g = float(features.get("growth", 0.0))

        score = 0.40 * d + 0.25 * s + 0.20 * c + 0.15 * g
        return max(0.0, min(100.0, score))


# Stubs reserved for future Phase ML pipelines (no training executed in Phase 5)

class RandomForestRiskModel(BaseRiskModel):
    """
    Reserved interface for trained Scikit-Learn Random Forest Regressor.
    """
    def predict(self, features: Dict[str, float]) -> float:
        raise NotImplementedError("RandomForestRiskModel reserved for future ML phases.")


class XGBoostRiskModel(BaseRiskModel):
    """
    Reserved interface for trained XGBoost Gradient Boosting model.
    """
    def predict(self, features: Dict[str, float]) -> float:
        raise NotImplementedError("XGBoostRiskModel reserved for future ML phases.")


class LSTMRiskModel(BaseRiskModel):
    """
    Reserved interface for trained PyTorch LSTM sequential model.
    """
    def predict(self, features: Dict[str, float]) -> float:
        raise NotImplementedError("LSTMRiskModel reserved for future ML phases.")

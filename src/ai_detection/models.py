"""
Data Models for Resume AI Detection Module
Pure Python Standard Library Dataclasses.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class FeatureResult:
    """
    Represents the output score, weight, and explanation for a single stylometric feature.
    """
    feature_name: str
    raw_value: float
    normalized_score: float  # 0.0 to 100.0
    weight: float             # e.g., 0.30 for 30%
    contribution: float       # normalized_score * weight
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature_name": self.feature_name,
            "raw_value": round(self.raw_value, 4),
            "normalized_score": round(self.normalized_score, 2),
            "weight": round(self.weight, 4),
            "contribution": round(self.contribution, 2),
            "explanation": self.explanation
        }


@dataclass
class AIDetectionResult:
    """
    Represents the comprehensive explainable AI likelihood analysis output.
    """
    ai_likelihood_score: float  # 0.0 to 100.0
    confidence: str              # "Low", "Moderate", "High"
    category: str                # e.g., "Low AI-style signals"
    signals: List[str] = field(default_factory=list)
    feature_breakdown: List[FeatureResult] = field(default_factory=list)
    disclaimer: str = (
        "Notice: This score reflects statistical and stylometric resemblance to common AI-generated text patterns. "
        "It is a heuristic likelihood indicator and does NOT constitute proof of AI generation."
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ai_likelihood_score": round(self.ai_likelihood_score, 2),
            "confidence": self.confidence,
            "category": self.category,
            "signals": self.signals,
            "feature_breakdown": [f.to_dict() for f in self.feature_breakdown],
            "disclaimer": self.disclaimer
        }

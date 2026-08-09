"""
Transparent Weighted Scoring Engine and Explanation Generator for AI Detection
Pure Python Standard Library.
"""
from typing import List, Dict, Any, Tuple
from .models import FeatureResult, AIDetectionResult


class ScoringEngine:
    """
    Computes weighted normalized feature sub-scores, overall AI likelihood score,
    and natural language explanations.
    """

    # Feature Weights (Sum = 1.0)
    WEIGHTS: Dict[str, float] = {
        "cliche_density": 0.30,
        "sentence_burstiness": 0.20,
        "transition_density": 0.20,
        "ngram_predictability": 0.15,
        "lexical_diversity": 0.05,
        "repetition_index": 0.05,
        "structural_consistency": 0.05
    }

    @classmethod
    def score_cliche_density(cls, stats: Dict[str, Any]) -> FeatureResult:
        density = stats.get("density_per_100", 0.0)
        matches = stats.get("matches", [])

        # Density >= 3.0 matches per 100 words yields 100% normalized score
        normalized = min(100.0, density * 33.33)
        weight = cls.WEIGHTS["cliche_density"]
        contribution = normalized * weight

        if matches:
            unique_matches = sorted(list(set(matches)))[:5]
            explanation = (
                f"Found {len(matches)} generic/cliché phrases ({density:.1f} per 100 words), "
                f"including: {', '.join(unique_matches)}."
            )
        else:
            explanation = "No generic professional clichés or overused LLM tokens detected."

        return FeatureResult(
            feature_name="Generic / Cliché Phrase Density",
            raw_value=density,
            normalized_score=normalized,
            weight=weight,
            contribution=contribution,
            explanation=explanation
        )

    @classmethod
    def score_sentence_burstiness(cls, stats: Dict[str, float]) -> FeatureResult:
        cv = stats.get("cv", 0.0)
        count = stats.get("count", 0)
        weight = cls.WEIGHTS["sentence_burstiness"]

        if count < 2:
            normalized = 0.0
            explanation = "Insufficient sentences for sentence-length burstiness calculation."
        else:
            # Low CV (< 0.25) indicates uniform AI-style sentence lengths (high score)
            # High CV (> 0.65) indicates human burstiness (low score)
            if cv <= 0.20:
                normalized = 100.0
            elif cv >= 0.70:
                normalized = 0.0
            else:
                normalized = (0.70 - cv) / 0.50 * 100.0

            normalized = max(0.0, min(100.0, normalized))
            explanation = (
                f"Sentence length Variation Index (CV) is {cv:.2f} across {count} sentences. "
                f"{'Low variation indicates uniform, structured sentences.' if cv < 0.35 else 'Natural sentence length variation detected.'}"
            )

        return FeatureResult(
            feature_name="Sentence Length Burstiness",
            raw_value=cv,
            normalized_score=normalized,
            weight=weight,
            contribution=normalized * weight,
            explanation=explanation
        )

    @classmethod
    def score_transition_density(cls, stats: Dict[str, Any]) -> FeatureResult:
        density = stats.get("density_per_10", 0.0)
        matches = stats.get("matches", [])
        weight = cls.WEIGHTS["transition_density"]

        normalized = min(100.0, density * 50.0)
        contribution = normalized * weight

        if matches:
            explanation = (
                f"Detected {len(matches)} sentence-starting transition phrases "
                f"({density:.1f} per 10 sentences): {', '.join(set(matches))}."
            )
        else:
            explanation = "No repetitive sentence-starting transition phrases detected."

        return FeatureResult(
            feature_name="Transition Phrase Density",
            raw_value=density,
            normalized_score=normalized,
            weight=weight,
            contribution=contribution,
            explanation=explanation
        )

    @classmethod
    def score_ngram_predictability(cls, stats: Dict[str, Any]) -> FeatureResult:
        rep_ratio = stats.get("repetition_ratio", 0.0)
        weight = cls.WEIGHTS["ngram_predictability"]

        normalized = min(100.0, rep_ratio * 250.0)
        contribution = normalized * weight

        explanation = (
            f"N-gram predictability proxy repetition ratio is {rep_ratio:.1%}. "
            f"{'High n-gram repetition detected.' if rep_ratio > 0.20 else 'Low n-gram repetition ratio.'}"
        )

        return FeatureResult(
            feature_name="N-Gram Predictability Proxy",
            raw_value=rep_ratio,
            normalized_score=normalized,
            weight=weight,
            contribution=contribution,
            explanation=explanation
        )

    @classmethod
    def score_lexical_diversity(cls, stats: Dict[str, float]) -> FeatureResult:
        ttr = stats.get("ttr", 1.0)
        weight = cls.WEIGHTS["lexical_diversity"]

        # Lower TTR (< 0.45) increases score mildy; High TTR (> 0.75) reduces score
        if ttr >= 0.75:
            normalized = 0.0
        elif ttr <= 0.35:
            normalized = 100.0
        else:
            normalized = (0.75 - ttr) / 0.40 * 100.0

        normalized = max(0.0, min(100.0, normalized))
        contribution = normalized * weight

        explanation = (
            f"Lexical Diversity (Type-Token Ratio) is {ttr:.1%} "
            f"({stats.get('unique', 0)} unique words out of {stats.get('total', 0)} total tokens)."
        )

        return FeatureResult(
            feature_name="Lexical Diversity",
            raw_value=ttr,
            normalized_score=normalized,
            weight=weight,
            contribution=contribution,
            explanation=explanation
        )

    @classmethod
    def score_repetition_index(cls, stats: Dict[str, Any]) -> FeatureResult:
        rep_score = stats.get("repetition_score", 0.0)
        duplicates = stats.get("duplicates", [])
        weight = cls.WEIGHTS["repetition_index"]

        normalized = min(100.0, rep_score * 2.5)
        contribution = normalized * weight

        if duplicates:
            explanation = f"Detected {len(duplicates)} repeated sentence patterns."
        else:
            explanation = "No duplicate sentence patterns detected."

        return FeatureResult(
            feature_name="Repetition Index",
            raw_value=rep_score,
            normalized_score=normalized,
            weight=weight,
            contribution=contribution,
            explanation=explanation
        )

    @classmethod
    def score_structural_consistency(cls, stats: Dict[str, float]) -> FeatureResult:
        consistency = stats.get("consistency_score", 50.0)
        weight = cls.WEIGHTS["structural_consistency"]

        normalized = max(0.0, min(100.0, consistency))
        contribution = normalized * weight

        explanation = f"Structural bullet length uniformity score is {consistency:.1f}/100."

        return FeatureResult(
            feature_name="Formatting / Structural Consistency",
            raw_value=consistency,
            normalized_score=normalized,
            weight=weight,
            contribution=contribution,
            explanation=explanation
        )

    @classmethod
    def calculate_category_and_confidence(
        cls, final_score: float, total_words: int, total_sentences: int
    ) -> Tuple[str, str]:
        """
        Determines heuristic category and assessment confidence level.
        """
        # Category classification
        if final_score <= 30.0:
            category = "Low AI-style signals"
        elif final_score <= 60.0:
            category = "Moderate AI-style signals"
        elif final_score <= 80.0:
            category = "High AI-style signals"
        else:
            category = "Very high AI-style signals"

        # Confidence level
        if total_words < 40 or total_sentences < 3:
            confidence = "Low"
        elif total_words < 100:
            confidence = "Moderate"
        else:
            confidence = "High"

        return category, confidence

    @classmethod
    def generate_signals(cls, feature_results: List[FeatureResult]) -> List[str]:
        """
        Generates human-readable summary bullet points highlighting key signal drivers.
        """
        signals = []
        for f in feature_results:
            if f.normalized_score >= 65.0:
                signals.append(f"High {f.feature_name.lower()}")
            elif f.normalized_score >= 35.0:
                signals.append(f"Moderate {f.feature_name.lower()}")

        if not signals:
            signals.append("Low overall AI-style stylometric signals across all metrics.")

        return signals

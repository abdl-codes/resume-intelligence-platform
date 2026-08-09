"""
Orchestrator Detector Class for Resume AI Likelihood Analysis
Pure Python Standard Library.
"""
from typing import Union
from src.core.models import ResumeDocument
from src.core.section_parser import SectionParser

from .models import AIDetectionResult, FeatureResult
from .features import FeatureExtractor
from .scoring import ScoringEngine


class AIDetector:
    """
    Local, explainable AI-generated likelihood detection engine.
    Computes statistical and stylometric signals without external dependencies or APIs.
    """

    @classmethod
    def analyze(cls, document: Union[ResumeDocument, str], file_name: str = "") -> AIDetectionResult:
        """
        Analyzes a raw resume string or ingested ResumeDocument and returns an AIDetectionResult.
        """
        if isinstance(document, str):
            doc = SectionParser.parse_resume(document, file_name=file_name)
        else:
            doc = document

        # Edge case handling: Empty or very short text
        if not doc.tokens or not doc.raw_text.strip():
            return AIDetectionResult(
                ai_likelihood_score=0.0,
                confidence="Low",
                category="Low AI-style signals",
                signals=["Empty or insufficient text provided for analysis."],
                feature_breakdown=[]
            )

        # 1. Feature Extraction
        sentence_stats = FeatureExtractor.sentence_length_stats(doc.sentences)
        ngram_stats = FeatureExtractor.ngram_predictability_proxy(doc.tokens)
        cliche_stats = FeatureExtractor.cliche_phrase_density(doc.raw_text, doc.filtered_tokens)
        transition_stats = FeatureExtractor.transition_phrase_density(doc.sentences)
        lexical_stats = FeatureExtractor.lexical_diversity(doc.tokens)
        repetition_stats = FeatureExtractor.repetition_index(doc.sentences)
        structural_stats = FeatureExtractor.structural_consistency(doc)

        # 2. Feature Scoring
        feature_results: List[FeatureResult] = [
            ScoringEngine.score_cliche_density(cliche_stats),
            ScoringEngine.score_sentence_burstiness(sentence_stats),
            ScoringEngine.score_transition_density(transition_stats),
            ScoringEngine.score_ngram_predictability(ngram_stats),
            ScoringEngine.score_lexical_diversity(lexical_stats),
            ScoringEngine.score_repetition_index(repetition_stats),
            ScoringEngine.score_structural_consistency(structural_stats)
        ]

        # 3. Overall Weighted Score Calculation
        total_score = sum(f.contribution for f in feature_results)
        final_score = max(0.0, min(100.0, total_score))

        # 4. Category, Confidence, and Signal Explanations
        category, confidence = ScoringEngine.calculate_category_and_confidence(
            final_score, len(doc.tokens), len(doc.sentences)
        )
        signals = ScoringEngine.generate_signals(feature_results)

        return AIDetectionResult(
            ai_likelihood_score=final_score,
            confidence=confidence,
            category=category,
            signals=signals,
            feature_breakdown=feature_results
        )

"""
Stylometric Feature Extractor for Resume AI Likelihood Detection
Pure Python Standard Library. Reuses Stage 1 Core Processing utilities.
"""
import re
import math
from collections import Counter
from typing import List, Tuple, Dict, Set, Any

from src.core.models import ResumeDocument
from src.core.text_processing import (
    tokenize,
    split_sentences,
    remove_stopwords,
    get_ngrams
)


# Transparent, editable dictionary of professional clichés and LLM overused tokens
CLICHE_PHRASES: List[str] = [
    "results-driven",
    "highly motivated",
    "passionate about",
    "proven track record",
    "strong communication skills",
    "team player",
    "detail-oriented",
    "think outside the box",
    "dynamic professional",
    "track record of success",
    "self-starter",
    "fast-paced environment",
    "strategic thinker",
    "go-getter",
    "thought leader"
]

CLICHE_TOKENS: Set[str] = {
    "delve", "spearheaded", "realm", "synergy", "testament",
    "pivotal", "transformative", "beacon", "mastery", "tapestry",
    "seamless", "cutting-edge", "paramount", "underscores"
}

TRANSITION_STARTERS: List[str] = [
    "additionally",
    "furthermore",
    "moreover",
    "in addition",
    "consequently",
    "in summary",
    "crucial to this",
    "as a result",
    "it is worth noting",
    "importantly"
]


class FeatureExtractor:
    """
    Extracts statistical and stylometric features from processed resume text.
    """

    @staticmethod
    def sentence_length_stats(sentences: List[str]) -> Dict[str, float]:
        """
        Calculates sentence word count statistics: mean, variance, standard deviation, and CV (burstiness).
        """
        if not sentences:
            return {"count": 0, "mean": 0.0, "variance": 0.0, "std_dev": 0.0, "cv": 0.0}

        word_counts = [len(tokenize(s)) for s in sentences if s.strip()]
        if not word_counts:
            return {"count": 0, "mean": 0.0, "variance": 0.0, "std_dev": 0.0, "cv": 0.0}

        n = len(word_counts)
        mean = sum(word_counts) / n
        if n <= 1 or mean == 0:
            return {"count": n, "mean": mean, "variance": 0.0, "std_dev": 0.0, "cv": 0.0}

        variance = sum((x - mean) ** 2 for x in word_counts) / n
        std_dev = math.sqrt(variance)
        cv = std_dev / mean

        return {
            "count": n,
            "mean": mean,
            "variance": variance,
            "std_dev": std_dev,
            "cv": cv
        }

    @staticmethod
    def ngram_predictability_proxy(tokens: List[str]) -> Dict[str, Any]:
        """
        Calculates n-gram repetition ratio as a proxy for phrase predictability.
        """
        if len(tokens) < 4:
            return {"repetition_ratio": 0.0, "bigram_count": 0, "trigram_count": 0}

        bigrams = get_ngrams(tokens, 2)
        trigrams = get_ngrams(tokens, 3)

        total_ngrams = len(bigrams) + len(trigrams)
        if total_ngrams == 0:
            return {"repetition_ratio": 0.0, "bigram_count": 0, "trigram_count": 0}

        unique_bigrams = len(set(bigrams))
        unique_trigrams = len(set(trigrams))
        unique_ngrams = unique_bigrams + unique_trigrams

        repetition_ratio = (total_ngrams - unique_ngrams) / total_ngrams

        return {
            "repetition_ratio": repetition_ratio,
            "bigram_count": len(bigrams),
            "trigram_count": len(trigrams)
        }

    @staticmethod
    def cliche_phrase_density(text: str, tokens: List[str]) -> Dict[str, Any]:
        """
        Calculates frequency of generic professional phrases and LLM overused tokens per 100 words.
        """
        if not tokens:
            return {"density_per_100": 0.0, "matches": [], "count": 0}

        lower_text = text.lower()
        matched_phrases = []

        # Multi-word phrase matches
        for phrase in CLICHE_PHRASES:
            count = len(re.findall(r'\b' + re.escape(phrase) + r'\b', lower_text))
            if count > 0:
                matched_phrases.extend([phrase] * count)

        # Single word cliché token matches
        for t in tokens:
            if t.lower() in CLICHE_TOKENS:
                matched_phrases.append(t.lower())

        total_words = len(tokens)
        density = (len(matched_phrases) / total_words) * 100 if total_words > 0 else 0.0

        return {
            "density_per_100": density,
            "matches": matched_phrases,
            "count": len(matched_phrases)
        }

    @staticmethod
    def transition_phrase_density(sentences: List[str]) -> Dict[str, Any]:
        """
        Calculates density of generic transition starters per 10 sentences.
        """
        if not sentences:
            return {"density_per_10": 0.0, "matches": [], "count": 0}

        matched_transitions = []
        for s in sentences:
            cleaned_s = s.strip().lower()
            for transition in TRANSITION_STARTERS:
                if cleaned_s.startswith(transition):
                    matched_transitions.append(transition)
                    break

        total_sentences = len(sentences)
        density = (len(matched_transitions) / total_sentences) * 10 if total_sentences > 0 else 0.0

        return {
            "density_per_10": density,
            "matches": matched_transitions,
            "count": len(matched_transitions)
        }

    @staticmethod
    def lexical_diversity(tokens: List[str]) -> Dict[str, float]:
        """
        Calculates Type-Token Ratio (TTR) = unique words / total words.
        """
        if not tokens:
            return {"ttr": 1.0, "total": 0, "unique": 0}

        total = len(tokens)
        unique = len(set(t.lower() for t in tokens))
        ttr = unique / total if total > 0 else 1.0

        return {
            "ttr": ttr,
            "total": total,
            "unique": unique
        }

    @staticmethod
    def repetition_index(sentences: List[str]) -> Dict[str, Any]:
        """
        Detects exact and near-duplicate sentence repetitions.
        """
        if len(sentences) < 2:
            return {"repetition_score": 0.0, "duplicates": []}

        cleaned_sentences = [s.strip().lower() for s in sentences if len(s.strip()) > 5]
        counts = Counter(cleaned_sentences)
        duplicates = [s for s, count in counts.items() if count > 1]

        total = len(cleaned_sentences)
        rep_score = (sum(counts[s] - 1 for s in duplicates) / total) * 100 if total > 0 else 0.0

        return {
            "repetition_score": rep_score,
            "duplicates": duplicates
        }

    @staticmethod
    def structural_consistency(doc: ResumeDocument) -> Dict[str, float]:
        """
        Analyzes consistency in bullet point length variance and section lengths.
        """
        all_bullets = []
        for sec in doc.sections:
            all_bullets.extend(sec.bullet_points)

        if len(all_bullets) < 2:
            return {"bullet_length_cv": 0.5, "consistency_score": 50.0}

        lengths = [len(b.split()) for b in all_bullets]
        mean = sum(lengths) / len(lengths)
        if mean == 0:
            return {"bullet_length_cv": 0.0, "consistency_score": 50.0}

        variance = sum((x - mean) ** 2 for x in lengths) / len(lengths)
        std_dev = math.sqrt(variance)
        cv = std_dev / mean

        # Low variance (cv < 0.25) indicates high structural uniformity
        uniformity_score = max(0.0, min(100.0, (1.0 - cv) * 100))

        return {
            "bullet_length_cv": cv,
            "consistency_score": uniformity_score
        }

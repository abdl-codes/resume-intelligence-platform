"""
Resume ↔ Job Description Matching Package
"""
from .models import (
    SkillMatchItem,
    ComponentMatchResult,
    JDMatchResult,
    CandidateRankItem,
    CombinedVerificationResult
)
from .features import (
    MatchFeatures,
    SKILL_ALIASES,
    EDUCATION_DEGREES,
    GENERIC_NON_SKILL_WORDS,
    EDUCATION_TERMS,
    PREFERRED_SKILLS_SECTION_HEADERS,
    KEYWORD_GENERIC_WORDS,
    is_valid_skill,
    strip_resume_header,
    compute_keyword_rarity_weights,
    levenshtein_distance,
    normalized_levenshtein
)
from .scoring import ScoringEngine
from .matcher import JDMatcher

__all__ = [
    "SkillMatchItem",
    "ComponentMatchResult",
    "JDMatchResult",
    "CandidateRankItem",
    "CombinedVerificationResult",
    "MatchFeatures",
    "SKILL_ALIASES",
    "EDUCATION_DEGREES",
    "GENERIC_NON_SKILL_WORDS",
    "EDUCATION_TERMS",
    "PREFERRED_SKILLS_SECTION_HEADERS",
    "KEYWORD_GENERIC_WORDS",
    "is_valid_skill",
    "strip_resume_header",
    "compute_keyword_rarity_weights",
    "levenshtein_distance",
    "normalized_levenshtein",
    "ScoringEngine",
    "JDMatcher",
]


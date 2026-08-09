"""
Data Models for Resume ↔ Job Description Matching Engine
Pure Python Standard Library Dataclasses.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class SkillMatchItem:
    """
    Represents a match comparison between a JD skill requirement and candidate's resume skill.
    """
    jd_skill: str
    resume_skill: str
    similarity_score: float  # 0.0 to 1.0
    match_type: str          # "Exact", "Alias", "Fuzzy", "Missing"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "jd_skill": self.jd_skill,
            "resume_skill": self.resume_skill,
            "similarity_score": round(self.similarity_score, 2),
            "match_type": self.match_type
        }


@dataclass
class ComponentMatchResult:
    """
    Represents matching breakdown for a single JD component (Required Skills, Experience, etc.).

    is_active (Fix #2): True when the JD specifies this requirement;
    False when the requirement is absent (component excluded from scoring denominator).
    """
    component_name: str
    raw_value: float
    normalized_score: float  # 0.0 to 100.0
    weight: float             # e.g., 0.40 for 40%
    contribution: float       # normalized_score * weight
    status: str               # "Meets requirement", "Partially meets", "Does not meet", "Not Determined", "Not Applicable"
    is_active: bool = True    # False = component excluded from dynamic scoring (Fix #2)
    matched_items: List[str] = field(default_factory=list)
    missing_items: List[str] = field(default_factory=list)
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_name": self.component_name,
            "raw_value": round(self.raw_value, 2),
            "normalized_score": round(self.normalized_score, 2),
            "weight": round(self.weight, 4),
            "contribution": round(self.contribution, 2),
            "status": self.status,
            "is_active": self.is_active,
            "matched_items": self.matched_items,
            "missing_items": self.missing_items,
            "explanation": self.explanation
        }


@dataclass
class JDMatchResult:
    """
    Represents the full explainable matching result between a resume and job description.
    """
    candidate_name: str
    job_title: str
    overall_match_score: float  # 0.0 to 100.0
    component_breakdown: List[ComponentMatchResult] = field(default_factory=list)
    skill_matches: List[SkillMatchItem] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_name": self.candidate_name,
            "job_title": self.job_title,
            "overall_match_score": round(self.overall_match_score, 2),
            "component_breakdown": [c.to_dict() for c in self.component_breakdown],
            "skill_matches": [s.to_dict() for s in self.skill_matches]
        }


@dataclass
class CandidateRankItem:
    """
    Represents a candidate's position in a ranked candidate list.
    Rankings are based STRICTLY on Qualification Match Score.
    """
    rank: int
    candidate_name: str
    qualification_match_score: float
    ai_likelihood_score: Optional[float] = None
    ai_category: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "rank": self.rank,
            "candidate_name": self.candidate_name,
            "qualification_match_score": round(self.qualification_match_score, 2)
        }
        if self.ai_likelihood_score is not None:
            result["ai_likelihood_score"] = round(self.ai_likelihood_score, 2)
            result["ai_category"] = self.ai_category
        return result


@dataclass
class CombinedVerificationResult:
    """
    Combines Qualification Match Score and AI Likelihood Signal side-by-side as separate metrics.
    """
    candidate_name: str
    qualification_match_score: float
    ai_likelihood_score: float
    ai_category: str
    ai_confidence: str
    note: str = (
        "Note: Qualification Match Score evaluates skills/experience fit. "
        "AI-style Signal is a separate verification indicator and does NOT modify the qualification match score."
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_name": self.candidate_name,
            "qualification_match_score": round(self.qualification_match_score, 2),
            "ai_likelihood_score": round(self.ai_likelihood_score, 2),
            "ai_category": self.ai_category,
            "ai_confidence": self.ai_confidence,
            "note": self.note
        }

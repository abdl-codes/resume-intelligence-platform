"""
Weighted Match Scoring Engine for Resume ↔ Job Description Engine
Pure Python Standard Library.

Implements dynamic weight normalization (Fix #2, #6):
- When a JD does not specify a requirement (e.g., no certifications),
  that component is excluded and its weight redistributed.
- final_score = sum(active_score * active_weight) / sum(active_weights)
"""
from typing import List, Dict, Any, Optional, Tuple
from src.core.models import ResumeDocument, JobDescription
from src.core.text_processing import remove_stopwords
from .models import ComponentMatchResult, SkillMatchItem, JDMatchResult
from .features import MatchFeatures, compute_keyword_rarity_weights, KEYWORD_GENERIC_WORDS


class ScoringEngine:
    """
    Computes explainable, component-wise weighted match scores between Resumes and Job Descriptions.

    Dynamic normalization (Fix #2, #6):
    - Components whose JD requirements are absent are marked "Not Applicable"
      with is_active=False (score 0, weight excluded from denominator).
    - Active components have their weights normalized so the sum = 1.0.
    """

    # Configurable Default Component Weights (Total = 1.0)
    DEFAULT_WEIGHTS: Dict[str, float] = {
        "required_skills": 0.40,
        "preferred_skills": 0.10,
        "experience": 0.15,
        "education": 0.10,
        "certifications": 0.05,
        "responsibilities": 0.10,
        "keyword_relevance": 0.10
    }

    @classmethod
    def score_skill_category(
        cls,
        category_name: str,
        jd_skills: List[str],
        skill_matches: List[SkillMatchItem],
        weight: float
    ) -> ComponentMatchResult:
        """
        Scores Required Skills or Preferred Skills based on exact/alias/fuzzy match ratios.

        Fix #1/#2: When jd_skills is empty, returns is_active=False (no free points).
        """
        if not jd_skills:
            # No skills specified → NOT APPLICABLE, excluded from scoring (Fix #2)
            return ComponentMatchResult(
                component_name=category_name,
                raw_value=0.0,
                normalized_score=0.0,
                weight=weight,
                contribution=0.0,
                status="Not Applicable",
                is_active=False,
                matched_items=[],
                missing_items=[],
                explanation=f"No explicit {category_name.lower()} specified in Job Description. Component excluded from scoring."
            )

        cat_matches = [s for s in skill_matches if s.jd_skill in jd_skills]
        if not cat_matches:
            return ComponentMatchResult(
                component_name=category_name,
                raw_value=0.0,
                normalized_score=0.0,
                weight=weight,
                contribution=0.0,
                is_active=True,
                status="Does not meet",
                matched_items=[],
                missing_items=jd_skills,
                explanation=f"None of the {len(jd_skills)} required skills were found in the candidate resume."
            )

        matched_items = [f"{s.jd_skill} ({s.match_type})" for s in cat_matches if s.match_type != "Missing"]
        missing_items = [s.jd_skill for s in cat_matches if s.match_type == "Missing"]

        matched_count = len(matched_items)
        total_count = len(jd_skills)

        normalized_score = (matched_count / total_count) * 100.0 if total_count > 0 else 0.0
        contribution = normalized_score * weight

        if normalized_score >= 100.0:
            status = "Meets requirement"
        elif normalized_score > 0.0:
            status = "Partially meets"
        else:
            status = "Does not meet"

        explanation = f"Matched {matched_count} out of {total_count} {category_name.lower()}."

        return ComponentMatchResult(
            component_name=category_name,
            raw_value=normalized_score,
            normalized_score=normalized_score,
            weight=weight,
            contribution=contribution,
            status=status,
            is_active=True,
            matched_items=matched_items,
            missing_items=missing_items,
            explanation=explanation
        )

    @classmethod
    def score_experience(
        cls,
        required_years: Optional[float],
        detected_years: Optional[float],
        weight: float
    ) -> ComponentMatchResult:
        """
        Scores candidate experience against JD required experience.

        Fix #2: When required_years is None, returns is_active=False.
        """
        if required_years is None:
            return ComponentMatchResult(
                component_name="Experience",
                raw_value=0.0,
                normalized_score=0.0,
                weight=weight,
                contribution=0.0,
                status="Not Applicable",
                is_active=False,
                matched_items=[],
                missing_items=[],
                explanation="No explicit experience duration requirement specified in Job Description. Component excluded from scoring."
            )

        if detected_years is None:
            return ComponentMatchResult(
                component_name="Experience",
                raw_value=0.0,
                normalized_score=0.0,
                weight=weight,
                contribution=0.0,
                status="Not Determined",
                is_active=True,
                matched_items=[],
                missing_items=[f"Required: {required_years:.1f}+ years"],
                explanation=f"Required: {required_years:.1f}+ years. Stated candidate experience could not be reliably determined."
            )

        if detected_years >= required_years:
            score = 100.0
            status = "Meets requirement"
        elif detected_years > 0:
            score = (detected_years / required_years) * 100.0
            status = "Partially meets"
        else:
            score = 0.0
            status = "Does not meet"

        explanation = f"Required: {required_years:.1f}+ years | Detected: {detected_years:.1f} years."

        return ComponentMatchResult(
            component_name="Experience",
            raw_value=score,
            normalized_score=score,
            weight=weight,
            contribution=score * weight,
            status=status,
            is_active=True,
            matched_items=[f"Detected {detected_years:.1f} yrs"],
            missing_items=[] if score >= 100 else [f"Short by {required_years - detected_years:.1f} yrs"],
            explanation=explanation
        )

    @classmethod
    def score_education(
        cls,
        required_degrees: List[str],
        candidate_degrees: List[str],
        weight: float
    ) -> ComponentMatchResult:
        """
        Scores candidate education degree requirements.

        Fix #2: When required_degrees is empty, returns is_active=False.
        """
        if not required_degrees:
            return ComponentMatchResult(
                component_name="Education",
                raw_value=0.0,
                normalized_score=0.0,
                weight=weight,
                contribution=0.0,
                status="Not Applicable",
                is_active=False,
                matched_items=candidate_degrees,
                missing_items=[],
                explanation="No explicit degree requirement specified in Job Description. Component excluded from scoring."
            )

        if not candidate_degrees:
            return ComponentMatchResult(
                component_name="Education",
                raw_value=0.0,
                normalized_score=0.0,
                weight=weight,
                contribution=0.0,
                status="Not Determined",
                is_active=True,
                matched_items=[],
                missing_items=required_degrees,
                explanation=f"Required degree: {', '.join(required_degrees)}. Candidate degree not specified or found."
            )

        matched = [d for d in required_degrees if d in candidate_degrees]
        if matched:
            score = 100.0
            status = "Meets requirement"
            explanation = f"Required degree ({', '.join(required_degrees)}) met by candidate ({', '.join(candidate_degrees)})."
        else:
            score = 50.0
            status = "Partially meets"
            explanation = f"Required: {', '.join(required_degrees)} | Candidate: {', '.join(candidate_degrees)}."

        return ComponentMatchResult(
            component_name="Education",
            raw_value=score,
            normalized_score=score,
            weight=weight,
            contribution=score * weight,
            status=status,
            is_active=True,
            matched_items=candidate_degrees,
            missing_items=[d for d in required_degrees if d not in candidate_degrees],
            explanation=explanation
        )

    @classmethod
    def score_certifications(
        cls,
        required_certs: List[str],
        candidate_certs: List[str],
        weight: float
    ) -> ComponentMatchResult:
        """
        Scores candidate certifications.

        Fix #2: When required_certs is empty, returns is_active=False.
        """
        if not required_certs:
            return ComponentMatchResult(
                component_name="Certifications",
                raw_value=0.0,
                normalized_score=0.0,
                weight=weight,
                contribution=0.0,
                status="Not Applicable",
                is_active=False,
                matched_items=candidate_certs,
                missing_items=[],
                explanation="No explicit certifications specified in Job Description. Component excluded from scoring."
            )

        matched = [c for c in required_certs if c.lower() in [cand.lower() for cand in candidate_certs]]
        missing = [c for c in required_certs if c.lower() not in [cand.lower() for cand in candidate_certs]]

        score = (len(matched) / len(required_certs)) * 100.0 if required_certs else 100.0
        status = "Meets requirement" if score >= 100 else ("Partially meets" if score > 0 else "Does not meet")

        return ComponentMatchResult(
            component_name="Certifications",
            raw_value=score,
            normalized_score=score,
            weight=weight,
            contribution=score * weight,
            status=status,
            is_active=True,
            matched_items=matched,
            missing_items=missing,
            explanation=f"Matched {len(matched)} out of {len(required_certs)} required certifications."
        )

    @classmethod
    def score_keyword_relevance(
        cls,
        jd_filtered_tokens: List[str],
        resume_filtered_tokens: List[str],
        weight: float
    ) -> ComponentMatchResult:
        """
        Scores text-overlap keyword relevance using rarity-weighted token matching.

        Fix #5: Uses lightweight rarity/importance weighting so that technical
        terms count more than generic corporate words.
        """
        if not jd_filtered_tokens:
            return ComponentMatchResult(
                component_name="Keyword Relevance",
                raw_value=100.0,
                normalized_score=100.0,
                weight=weight,
                contribution=100.0 * weight,
                status="Not Applicable",
                is_active=True,
                matched_items=[],
                missing_items=[],
                explanation="No keywords available in Job Description."
            )

        jd_set = set(t.lower() for t in jd_filtered_tokens if len(t) > 3)
        res_set = set(t.lower() for t in resume_filtered_tokens if len(t) > 3)

        if not jd_set:
            return ComponentMatchResult(
                component_name="Keyword Relevance",
                raw_value=100.0,
                normalized_score=100.0,
                weight=weight,
                contribution=100.0 * weight,
                status="Not Applicable",
                is_active=True,
                matched_items=[],
                missing_items=[],
                explanation="No significant keywords found in Job Description."
            )

        # Compute rarity weights (Fix #5)
        rarity_weights = compute_keyword_rarity_weights(jd_set, res_set)

        overlap = jd_set.intersection(res_set)
        missing = jd_set.difference(res_set)

        # Weighted score: sum of matched weights / sum of all weights
        total_weight = sum(rarity_weights.get(t, 1.0) for t in jd_set)
        matched_weight = sum(rarity_weights.get(t, 1.0) for t in overlap)

        score = (matched_weight / total_weight) * 100.0 if total_weight > 0 else 0.0

        matched_sample = sorted(list(overlap))[:10]
        missing_sample = sorted(list(missing))[:10]

        return ComponentMatchResult(
            component_name="Keyword Relevance",
            raw_value=score,
            normalized_score=score,
            weight=weight,
            contribution=score * weight,
            status="Meets requirement" if score >= 70 else ("Partially meets" if score > 30 else "Does not meet"),
            is_active=True,
            matched_items=matched_sample,
            missing_items=missing_sample,
            explanation=f"Weighted keyword match: {matched_weight:.1f} / {total_weight:.1f} rarity-weighted points ({score:.1f}%)."
        )

    @classmethod
    def compute_dynamic_final_score(cls, components: List[ComponentMatchResult]) -> float:
        """
        Computes the final score using dynamic weight normalization (Fix #6).

        Formula:
            final_score = sum(active_component_score * active_component_weight)
                          / sum(active_component_weights)

        Only active components (where the JD actually specifies requirements)
        contribute to the final score. This always produces a value in [0, 100].
        """
        active_components = [c for c in components if c.is_active]

        if not active_components:
            return 0.0

        total_active_weight = sum(c.weight for c in active_components)

        if total_active_weight <= 0:
            return 0.0

        weighted_sum = sum(c.normalized_score * c.weight for c in active_components)
        raw_score = weighted_sum / total_active_weight

        return max(0.0, min(100.0, raw_score))

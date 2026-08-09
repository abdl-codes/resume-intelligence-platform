"""
Orchestrator Matcher, Candidate Ranker, and Combined Verification Engine
Pure Python Standard Library.
"""
from typing import Union, List, Tuple, Dict, Optional
from src.core.models import ResumeDocument, JobDescription
from src.core.section_parser import SectionParser
from src.core.text_processing import tokenize, remove_stopwords
from src.ai_detection.detector import AIDetector

from .models import (
    SkillMatchItem,
    ComponentMatchResult,
    JDMatchResult,
    CandidateRankItem,
    CombinedVerificationResult
)
from .features import MatchFeatures, is_valid_skill, strip_resume_header
from .scoring import ScoringEngine


class JDMatcher:
    """
    Local, transparent Resume ↔ Job Description matching engine.
    """

    @classmethod
    def match(
        cls,
        resume: Union[ResumeDocument, str],
        jd: Union[JobDescription, str],
        candidate_name: str = "Candidate",
        custom_weights: Optional[Dict[str, float]] = None
    ) -> JDMatchResult:
        """
        Calculates an explainable qualification match score between a candidate's resume and a job description.
        """
        # Parse text if strings are passed
        res_doc = SectionParser.parse_resume(resume) if isinstance(resume, str) else resume
        jd_doc = SectionParser.parse_job_description(jd) if isinstance(jd, str) else jd

        weights = custom_weights or ScoringEngine.DEFAULT_WEIGHTS

        # Edge case: Empty resume or empty JD
        if not res_doc.tokens or not jd_doc.tokens:
            return JDMatchResult(
                candidate_name=candidate_name,
                job_title=jd_doc.title or "Job Position",
                overall_match_score=0.0,
                component_breakdown=[],
                skill_matches=[]
            )

        # 1. Skill Extraction & Matching (Required Skills)
        jd_skills_section = jd_doc.get_section("skills")
        jd_skills = MatchFeatures.extract_skills_from_text(jd_skills_section.raw_text) if jd_skills_section else []
        if not jd_skills:
            # Fall back to extracting technical tokens from JD using is_valid_skill
            jd_skills = [t for t in set(jd_doc.filtered_tokens) if is_valid_skill(t)][:15]

        res_skills_section = res_doc.get_section("skills")
        res_skills = MatchFeatures.extract_skills_from_text(res_skills_section.raw_text) if res_skills_section else []
        if not res_skills:
            res_skills = [t for t in set(res_doc.filtered_tokens) if is_valid_skill(t)]

        skill_matches = MatchFeatures.match_skills(jd_skills, res_skills, res_doc.tokens)

        # 1b. Preferred Skills Extraction from JD (Fix #1)
        jd_preferred_skills = MatchFeatures.extract_preferred_skills_from_jd(jd_doc)
        preferred_skill_matches = MatchFeatures.match_skills(
            jd_preferred_skills, res_skills, res_doc.tokens
        ) if jd_preferred_skills else []

        # 2. Experience Extraction & Matching
        jd_req_exp = MatchFeatures.parse_experience_years(jd_doc.raw_text)
        cand_exp = MatchFeatures.parse_experience_years(res_doc.raw_text)

        # 3. Education Extraction & Matching
        jd_req_edu = MatchFeatures.parse_education_degrees(jd_doc.raw_text)
        cand_edu = MatchFeatures.parse_education_degrees(res_doc.raw_text)

        # 4. Certifications Matching
        jd_req_certs = MatchFeatures.parse_certifications(jd_doc.raw_text)
        cand_certs = MatchFeatures.parse_certifications(res_doc.raw_text)

        # 5. Keyword Relevance — using body text only (Fix #4: strip header/contact info)
        resume_body_text = strip_resume_header(res_doc)
        resume_body_tokens = tokenize(resume_body_text)
        resume_body_filtered = remove_stopwords(resume_body_tokens)

        # 6. Component Scoring
        components: List[ComponentMatchResult] = [
            ScoringEngine.score_skill_category("Required Skills", jd_skills, skill_matches, weights.get("required_skills", 0.40)),
            ScoringEngine.score_skill_category("Preferred Skills", jd_preferred_skills, preferred_skill_matches, weights.get("preferred_skills", 0.10)),
            ScoringEngine.score_experience(jd_req_exp, cand_exp, weights.get("experience", 0.15)),
            ScoringEngine.score_education(jd_req_edu, cand_edu, weights.get("education", 0.10)),
            ScoringEngine.score_certifications(jd_req_certs, cand_certs, weights.get("certifications", 0.05)),
            ScoringEngine.score_keyword_relevance(jd_doc.filtered_tokens, resume_body_filtered, weights.get("keyword_relevance", 0.10) + weights.get("responsibilities", 0.10))
        ]

        # 7. Dynamic Final Score (Fix #6)
        overall_match_score = ScoringEngine.compute_dynamic_final_score(components)

        # Combine all skill matches for the result (required + preferred)
        all_skill_matches = skill_matches + preferred_skill_matches

        return JDMatchResult(
            candidate_name=candidate_name,
            job_title=jd_doc.title or "Job Position",
            overall_match_score=overall_match_score,
            component_breakdown=components,
            skill_matches=all_skill_matches
        )

    @classmethod
    def rank_candidates(
        cls,
        candidates: List[Tuple[str, Union[ResumeDocument, str]]],
        jd: Union[JobDescription, str],
        include_ai_signals: bool = True
    ) -> List[CandidateRankItem]:
        """
        Ranks multiple candidate resumes based STRICTLY on Qualification Match Score.
        Optionally attaches separate AI likelihood scores without affecting rank order.
        """
        match_results = []

        for name, res in candidates:
            match_res = cls.match(res, jd, candidate_name=name)
            ai_score = None
            ai_cat = None

            if include_ai_signals:
                ai_res = AIDetector.analyze(res)
                ai_score = ai_res.ai_likelihood_score
                ai_cat = ai_res.category

            match_results.append((match_res, ai_score, ai_cat))

        # Rank strictly by Qualification Match Score (descending)
        match_results.sort(key=lambda x: x[0].overall_match_score, reverse=True)

        ranked_list: List[CandidateRankItem] = []
        for idx, (m_res, ai_score, ai_cat) in enumerate(match_results, start=1):
            ranked_list.append(CandidateRankItem(
                rank=idx,
                candidate_name=m_res.candidate_name,
                qualification_match_score=m_res.overall_match_score,
                ai_likelihood_score=ai_score,
                ai_category=ai_cat
            ))

        return ranked_list

    @classmethod
    def combined_verification(
        cls,
        resume: Union[ResumeDocument, str],
        jd: Union[JobDescription, str],
        candidate_name: str = "Candidate"
    ) -> CombinedVerificationResult:
        """
        Generates a combined side-by-side verification report.
        Qualification Match Score and AI Likelihood Score are kept completely separate.
        """
        match_result = cls.match(resume, jd, candidate_name=candidate_name)
        ai_result = AIDetector.analyze(resume)

        return CombinedVerificationResult(
            candidate_name=candidate_name,
            qualification_match_score=match_result.overall_match_score,
            ai_likelihood_score=ai_result.ai_likelihood_score,
            ai_category=ai_result.category,
            ai_confidence=ai_result.confidence
        )

"""
Analysis Pipeline Orchestrator
Bridges the UI/API layer with Stage 1 (Core), Stage 2 (AI Detection),
and Stage 3 (JD Matching) engines. Contains no business logic of its own.
Pure Python Standard Library.
"""
import traceback
from typing import List, Tuple, Dict, Any, Optional

from src.core.section_parser import SectionParser
from src.core.models import ResumeDocument, JobDescription
from src.ai_detection.detector import AIDetector
from src.jd_matching.matcher import JDMatcher


# ---------------------------------------------------------------------------
# Input Validation Helpers
# ---------------------------------------------------------------------------

def validate_jd_text(jd_text: str) -> Tuple[bool, str]:
    """Validates job description text. Returns (is_valid, error_message)."""
    if not jd_text or not jd_text.strip():
        return False, "Job description is empty. Please provide a job description to analyze against."
    stripped = jd_text.strip()
    if len(stripped) < 20:
        return False, "Job description is too short. Please provide more detail about the role requirements."
    return True, ""


def validate_resume_text(text: str, filename: str = "") -> Tuple[bool, str]:
    """Validates a single resume text. Returns (is_valid, error_message)."""
    label = f"Resume '{filename}'" if filename else "Resume"
    if not text or not text.strip():
        return False, f"{label} is empty or could not be read."
    stripped = text.strip()
    if len(stripped) < 15:
        return False, f"{label} is too short to analyze meaningfully ({len(stripped)} characters)."
    return True, ""


def _extract_candidate_name(doc: ResumeDocument, filename: str) -> str:
    """
    Attempts to extract a candidate name from the resume header section.
    Falls back to a cleaned-up filename if no name is detected.
    """
    # Check the first section (usually Header) for a plausible name line
    if doc.sections:
        header = doc.sections[0]
        lines = header.raw_text.split("\n")
        for line in lines[:5]:
            stripped = line.strip()
            # Skip empty lines, email-like lines, phone-like lines, links
            if not stripped:
                continue
            if "@" in stripped or "http" in stripped.lower():
                continue
            if any(c.isdigit() for c in stripped) and len(stripped) < 20:
                continue
            # A plausible name line: 2-4 words, mostly alpha
            words = stripped.split()
            if 1 <= len(words) <= 5:
                alpha_ratio = sum(1 for w in words if w.replace(".", "").isalpha()) / len(words)
                if alpha_ratio >= 0.6 and len(stripped) >= 3:
                    return stripped

    # Fallback: derive from filename
    if filename:
        import re as _re
        name = filename.rsplit(".", 1)[0]  # remove extension
        name = _re.sub(r'[_\-]+', ' ', name)  # underscores/hyphens → spaces
        name = _re.sub(r'(?i)\b(resume|cv|curriculum)\b', '', name).strip()
        if name:
            return name.title()

    return "Candidate"


# ---------------------------------------------------------------------------
# Core Orchestration
# ---------------------------------------------------------------------------

def process_single_resume(
    resume_text: str,
    jd_doc: JobDescription,
    filename: str = ""
) -> Dict[str, Any]:
    """
    Processes a single resume against an already-parsed JD.
    Returns a structured dict with qualification match, AI signals, and metadata.
    """
    # Validate
    valid, err = validate_resume_text(resume_text, filename)
    if not valid:
        return {
            "status": "error",
            "filename": filename,
            "candidate_name": filename or "Unknown",
            "error": err,
        }

    try:
        # Stage 1 — Parse resume
        resume_doc = SectionParser.parse_resume(resume_text, file_name=filename)

        # Derive candidate name
        candidate_name = _extract_candidate_name(resume_doc, filename)

        # Stage 2 — AI-style detection (fully independent)
        ai_result = AIDetector.analyze(resume_doc)

        # Stage 3 — JD matching (fully independent)
        match_result = JDMatcher.match(resume_doc, jd_doc, candidate_name=candidate_name)

        # Determine status label based on qualification match
        q_score = match_result.overall_match_score
        if q_score >= 80:
            status_label = "Strong Match"
        elif q_score >= 60:
            status_label = "Good Match"
        elif q_score >= 40:
            status_label = "Moderate Match"
        else:
            status_label = "Weak Match"

        return {
            "status": "success",
            "filename": filename,
            "candidate_name": candidate_name,
            "qualification_match": match_result.to_dict(),
            "ai_detection": ai_result.to_dict(),
            "status_label": status_label,
        }

    except Exception as exc:
        return {
            "status": "error",
            "filename": filename,
            "candidate_name": filename or "Unknown",
            "error": f"Failed to process resume '{filename}': {str(exc)}",
            "traceback": traceback.format_exc(),
        }


def run_full_analysis(
    jd_text: str,
    resumes: List[Tuple[str, str]],
) -> Dict[str, Any]:
    """
    Main orchestration entry-point.

    Args:
        jd_text: Raw job description text.
        resumes: List of (filename, resume_text) tuples.

    Returns:
        Structured analysis report dict with summary, ranked candidates, and details.
    """
    # Validate JD
    jd_valid, jd_err = validate_jd_text(jd_text)
    if not jd_valid:
        return {"status": "error", "error": jd_err}

    # Validate at least one resume
    if not resumes:
        return {"status": "error", "error": "No resumes provided. Please upload at least one resume file."}

    # Stage 1 — Parse JD
    try:
        jd_doc = SectionParser.parse_job_description(jd_text)
    except Exception as exc:
        return {"status": "error", "error": f"Failed to parse job description: {str(exc)}"}

    # Process each resume
    candidate_results: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []

    for filename, resume_text in resumes:
        result = process_single_resume(resume_text, jd_doc, filename)
        if result["status"] == "error":
            errors.append({"filename": result["filename"], "error": result.get("error", "Unknown error")})
        else:
            candidate_results.append(result)

    if not candidate_results and errors:
        return {
            "status": "error",
            "error": "All resumes failed processing.",
            "file_errors": errors,
        }

    # Rank candidates strictly by qualification match (descending)
    candidate_results.sort(
        key=lambda c: c["qualification_match"]["overall_match_score"],
        reverse=True
    )

    # Assign ranks
    for idx, cand in enumerate(candidate_results, start=1):
        cand["rank"] = idx

    # Compute summary statistics
    total = len(candidate_results)
    scores = [c["qualification_match"]["overall_match_score"] for c in candidate_results]
    avg_score = sum(scores) / total if total > 0 else 0.0

    top_candidate = candidate_results[0]["candidate_name"] if candidate_results else "N/A"

    # "Requiring review" = candidates with AI-style signals in High or Very High category
    review_count = sum(
        1 for c in candidate_results
        if c["ai_detection"]["category"] in ("High AI-style signals", "Very high AI-style signals")
    )

    summary = {
        "total_candidates": total,
        "average_match_score": round(avg_score, 2),
        "top_candidate": top_candidate,
        "candidates_requiring_review": review_count,
    }

    return {
        "status": "success",
        "summary": summary,
        "candidates": candidate_results,
        "errors": errors,
    }

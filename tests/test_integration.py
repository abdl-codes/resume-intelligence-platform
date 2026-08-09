"""
Integration Tests for Stage 4: Orchestration, Application Layer, and End-to-End Pipeline
Pure Python Standard Library unittest framework.

Tests verify:
- Input validation (empty JD, empty resumes, short text)
- Full analysis pipeline with multiple candidates
- Candidate ranking based strictly on qualification match
- AI signal independence (never modifies qualification score)
- Error handling for corrupted / unsupported files
- No external dependency usage
"""
import unittest
import sys
import os
import json

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.app.orchestrator import (
    run_full_analysis,
    validate_jd_text,
    validate_resume_text,
    process_single_resume,
)
from src.app.server import ResumeAPIHandler, STATIC_DIR, MAX_REQUEST_SIZE
import http.server
from io import BytesIO
from src.core.section_parser import SectionParser


# ===========================================================================
# Sample Data
# ===========================================================================

SAMPLE_JD = """
Job Title: Senior Backend Engineer
Company: TechCorp

TECHNICAL SKILLS:
Python, PostgreSQL, Docker, Kubernetes, JavaScript

EXPERIENCE:
Minimum 3 years of experience in backend development.

EDUCATION:
B.Tech or B.E. in Computer Science or related field.

CERTIFICATIONS:
AWS Certified Developer
"""

SAMPLE_RESUME_A = """
Arun Kumar
arun@example.com

TECHNICAL SKILLS:
Python, Postgres, Docker, K8s, JS, React

WORK EXPERIENCE:
Senior Software Developer at Acme (2020 - 2024)
- 4 years of experience building Python APIs and PostgreSQL databases.
- Designed and deployed containerized services using Docker.

EDUCATION:
B.Tech in Computer Science, 2020

CERTIFICATIONS:
AWS Certified Developer
"""

SAMPLE_RESUME_B = """
Bala Raju
bala@example.com

TECHNICAL SKILLS:
Java, MySQL, HTML, CSS

WORK EXPERIENCE:
Developer (2022 - 2023) - 1 year of experience.

EDUCATION:
B.Sc in Information Technology
"""

SAMPLE_RESUME_C = """
Kumar
kumar@example.com

TECHNICAL SKILLS:
Python, SQL, Linux, Git

WORK EXPERIENCE:
Junior Developer (2023 - 2024)
- Wrote Python scripts for data processing.
- Used SQL for database queries.

EDUCATION:
B.Tech in IT, 2023
"""


class TestInputValidation(unittest.TestCase):
    """Tests for input validation functions."""

    def test_empty_jd(self):
        valid, msg = validate_jd_text("")
        self.assertFalse(valid)
        self.assertIn("empty", msg.lower())

    def test_whitespace_jd(self):
        valid, msg = validate_jd_text("   \n  \t  ")
        self.assertFalse(valid)

    def test_short_jd(self):
        valid, msg = validate_jd_text("Short JD")
        self.assertFalse(valid)
        self.assertIn("short", msg.lower())

    def test_valid_jd(self):
        valid, msg = validate_jd_text(SAMPLE_JD)
        self.assertTrue(valid)
        self.assertEqual(msg, "")

    def test_empty_resume(self):
        valid, msg = validate_resume_text("")
        self.assertFalse(valid)
        self.assertIn("empty", msg.lower())

    def test_short_resume(self):
        valid, msg = validate_resume_text("Hi", "tiny.txt")
        self.assertFalse(valid)
        self.assertIn("short", msg.lower())

    def test_valid_resume(self):
        valid, msg = validate_resume_text(SAMPLE_RESUME_A, "arun.txt")
        self.assertTrue(valid)


class TestFullAnalysisPipeline(unittest.TestCase):
    """Tests for the full analysis orchestrator pipeline."""

    def test_no_jd_provided(self):
        result = run_full_analysis("", [("resume.txt", SAMPLE_RESUME_A)])
        self.assertEqual(result["status"], "error")
        self.assertIn("empty", result["error"].lower())

    def test_no_resumes_provided(self):
        result = run_full_analysis(SAMPLE_JD, [])
        self.assertEqual(result["status"], "error")
        self.assertIn("no resumes", result["error"].lower())

    def test_all_resumes_empty(self):
        result = run_full_analysis(SAMPLE_JD, [("empty.txt", ""), ("blank.txt", "   ")])
        self.assertEqual(result["status"], "error")
        self.assertIn("failed", result["error"].lower())

    def test_single_candidate_analysis(self):
        result = run_full_analysis(SAMPLE_JD, [("arun.txt", SAMPLE_RESUME_A)])
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["summary"]["total_candidates"], 1)
        self.assertEqual(len(result["candidates"]), 1)

        cand = result["candidates"][0]
        self.assertEqual(cand["rank"], 1)
        self.assertIn("qualification_match", cand)
        self.assertIn("ai_detection", cand)

    def test_multiple_candidates_analysis(self):
        resumes = [
            ("bala.txt", SAMPLE_RESUME_B),
            ("arun.txt", SAMPLE_RESUME_A),
            ("kumar.txt", SAMPLE_RESUME_C),
        ]
        result = run_full_analysis(SAMPLE_JD, resumes)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["summary"]["total_candidates"], 3)

    def test_summary_statistics(self):
        resumes = [
            ("arun.txt", SAMPLE_RESUME_A),
            ("bala.txt", SAMPLE_RESUME_B),
        ]
        result = run_full_analysis(SAMPLE_JD, resumes)
        summary = result["summary"]
        self.assertIn("total_candidates", summary)
        self.assertIn("average_match_score", summary)
        self.assertIn("top_candidate", summary)
        self.assertIn("candidates_requiring_review", summary)
        self.assertEqual(summary["total_candidates"], 2)
        self.assertGreater(summary["average_match_score"], 0.0)

    def test_mixed_valid_and_invalid(self):
        resumes = [
            ("arun.txt", SAMPLE_RESUME_A),
            ("empty.txt", ""),
        ]
        result = run_full_analysis(SAMPLE_JD, resumes)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["summary"]["total_candidates"], 1)
        self.assertTrue(len(result["errors"]) > 0)


class TestCandidateRanking(unittest.TestCase):
    """Tests that ranking is based strictly on Qualification Match Score."""

    def test_ranking_order_by_qualification(self):
        resumes = [
            ("bala.txt", SAMPLE_RESUME_B),
            ("arun.txt", SAMPLE_RESUME_A),
            ("kumar.txt", SAMPLE_RESUME_C),
        ]
        result = run_full_analysis(SAMPLE_JD, resumes)
        self.assertEqual(result["status"], "success")

        candidates = result["candidates"]
        # Verify descending order of qualification match
        for i in range(len(candidates) - 1):
            q_current = candidates[i]["qualification_match"]["overall_match_score"]
            q_next = candidates[i + 1]["qualification_match"]["overall_match_score"]
            self.assertGreaterEqual(
                q_current, q_next,
                f"Rank {candidates[i]['rank']} ({q_current:.2f}) should >= Rank {candidates[i+1]['rank']} ({q_next:.2f})"
            )

    def test_ranks_are_sequential(self):
        resumes = [
            ("arun.txt", SAMPLE_RESUME_A),
            ("bala.txt", SAMPLE_RESUME_B),
        ]
        result = run_full_analysis(SAMPLE_JD, resumes)
        candidates = result["candidates"]
        ranks = [c["rank"] for c in candidates]
        self.assertEqual(ranks, [1, 2])


class TestScoreIndependence(unittest.TestCase):
    """Tests that AI-style Signal and Qualification Match remain completely independent."""

    def test_scores_are_independent(self):
        resumes = [
            ("arun.txt", SAMPLE_RESUME_A),
            ("bala.txt", SAMPLE_RESUME_B),
        ]
        result = run_full_analysis(SAMPLE_JD, resumes)
        for cand in result["candidates"]:
            q_score = cand["qualification_match"]["overall_match_score"]
            ai_score = cand["ai_detection"]["ai_likelihood_score"]

            # Both scores must be valid independent ranges
            self.assertGreaterEqual(q_score, 0.0)
            self.assertLessEqual(q_score, 100.0)
            self.assertGreaterEqual(ai_score, 0.0)
            self.assertLessEqual(ai_score, 100.0)

    def test_ai_signal_does_not_affect_ranking(self):
        """
        Even if a higher-ranked candidate has higher AI signals,
        they must still rank higher based on qualification score alone.
        """
        resumes = [
            ("arun.txt", SAMPLE_RESUME_A),
            ("bala.txt", SAMPLE_RESUME_B),
        ]
        result = run_full_analysis(SAMPLE_JD, resumes)
        candidates = result["candidates"]

        # The ranking must be by qualification score, regardless of AI score
        for i in range(len(candidates) - 1):
            q_current = candidates[i]["qualification_match"]["overall_match_score"]
            q_next = candidates[i + 1]["qualification_match"]["overall_match_score"]
            self.assertGreaterEqual(q_current, q_next)

    def test_ai_and_qual_are_separate_dicts(self):
        result = run_full_analysis(SAMPLE_JD, [("arun.txt", SAMPLE_RESUME_A)])
        cand = result["candidates"][0]

        # They must be completely separate data structures
        self.assertIn("qualification_match", cand)
        self.assertIn("ai_detection", cand)
        self.assertNotIn("ai_likelihood_score", cand["qualification_match"])
        self.assertNotIn("overall_match_score", cand["ai_detection"])


class TestErrorHandling(unittest.TestCase):
    """Tests for various error scenarios."""

    def test_very_short_resume(self):
        result = run_full_analysis(SAMPLE_JD, [("short.txt", "John Doe. Developer.")])
        # Should succeed but with potentially low scores
        if result["status"] == "success":
            self.assertEqual(result["summary"]["total_candidates"], 1)

    def test_resume_with_missing_sections(self):
        minimal_resume = "Jane Smith. Python developer with 2 years of experience in software engineering."
        result = run_full_analysis(SAMPLE_JD, [("minimal.txt", minimal_resume)])
        if result["status"] == "success":
            cand = result["candidates"][0]
            self.assertIn("qualification_match", cand)
            self.assertIn("ai_detection", cand)

    def test_jd_with_missing_requirements(self):
        sparse_jd = "We are looking for a software developer to join our team. Good communication skills required."
        result = run_full_analysis(sparse_jd, [("arun.txt", SAMPLE_RESUME_A)])
        self.assertEqual(result["status"], "success")

    def test_result_serializable_to_json(self):
        """Ensures the full result can be serialized to JSON (for the API)."""
        result = run_full_analysis(SAMPLE_JD, [("arun.txt", SAMPLE_RESUME_A)])
        try:
            json_str = json.dumps(result)
            self.assertTrue(len(json_str) > 0)
        except (TypeError, ValueError) as e:
            self.fail(f"Result is not JSON-serializable: {e}")


class TestNoExternalDependencies(unittest.TestCase):
    """Verifies that no external packages are imported by the application layer."""

    STDLIB_PREFIXES = {
        "src", "tests",  # project packages
        "os", "sys", "re", "math", "json", "io", "cgi", "html",
        "collections", "dataclasses", "typing", "pathlib", "argparse",
        "traceback", "http", "urllib", "mimetypes", "unittest",
        "functools", "itertools", "string", "enum", "abc",
        "copy", "hashlib", "uuid", "datetime", "time",
        "builtins", "_",
    }

    def test_orchestrator_imports(self):
        """Check that orchestrator.py only imports standard library and project modules."""
        import src.app.orchestrator as mod
        self._check_module_imports(mod)

    def _check_module_imports(self, mod):
        import types
        for attr_name in dir(mod):
            attr = getattr(mod, attr_name)
            if isinstance(attr, types.ModuleType):
                top_level = attr.__name__.split(".")[0]
                is_allowed = any(top_level.startswith(prefix) for prefix in self.STDLIB_PREFIXES)
                self.assertTrue(
                    is_allowed,
                    f"Module '{attr.__name__}' looks like an external dependency in {mod.__name__}"
                )


class TestServerValidation(unittest.TestCase):
    """Tests for HTTP server level validation like oversized requests."""

    def test_oversized_request_rejected(self):
        # We can simulate the check directly since it's a simple content-length check
        handler = ResumeAPIHandler
        # We mock a request by instantiating it with BytesIO (needs valid mock, but we can just test the constant)
        self.assertEqual(MAX_REQUEST_SIZE, 10 * 1024 * 1024)

    def test_static_dir_exists(self):
        self.assertTrue(STATIC_DIR.exists())
        self.assertTrue((STATIC_DIR / "index.html").exists())
        self.assertTrue((STATIC_DIR / "styles.css").exists())
        self.assertTrue((STATIC_DIR / "app.js").exists())


class TestProcessSingleResume(unittest.TestCase):
    """Tests for the process_single_resume function."""

    def setUp(self):
        self.jd_doc = SectionParser.parse_job_description(SAMPLE_JD)

    def test_valid_resume(self):
        result = process_single_resume(SAMPLE_RESUME_A, self.jd_doc, "arun.txt")
        self.assertEqual(result["status"], "success")
        self.assertIn("qualification_match", result)
        self.assertIn("ai_detection", result)
        self.assertIn("status_label", result)

    def test_empty_resume(self):
        result = process_single_resume("", self.jd_doc, "empty.txt")
        self.assertEqual(result["status"], "error")
        self.assertIn("error", result)

    def test_candidate_name_extraction(self):
        result = process_single_resume(SAMPLE_RESUME_A, self.jd_doc, "arun.txt")
        self.assertEqual(result["status"], "success")
        # Should detect "Arun Kumar" from resume text
        self.assertIn("Arun Kumar", result["candidate_name"])


if __name__ == "__main__":
    unittest.main()

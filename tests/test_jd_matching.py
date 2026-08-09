"""
Unit Tests for Stage 3: Resume ↔ Job Description Matching Engine
Pure Python Standard Library unittest framework.
"""
import unittest
from src.jd_matching import (
    JDMatcher,
    MatchFeatures,
    normalized_levenshtein,
    JDMatchResult,
    CombinedVerificationResult
)


class TestJDMatching(unittest.TestCase):

    def setUp(self):
        self.sample_jd = """
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

        self.sample_resume_a = """
        Arun Kumar
        arun@example.com

        TECHNICAL SKILLS:
        Python, Postgres, Docker, K8s, JS, React

        WORK EXPERIENCE:
        Senior Software Developer at Acme (2020 - 2024)
        - 4 years of experience building Python APIs and PostgreSQL databases.

        EDUCATION:
        B.Tech in Computer Science, 2020

        CERTIFICATIONS:
        AWS Certified Developer
        """

        self.sample_resume_b = """
        Bala Raju
        bala@example.com

        TECHNICAL SKILLS:
        Java, MySQL, HTML, CSS

        WORK EXPERIENCE:
        Developer (2022 - 2023) - 1 year of experience.

        EDUCATION:
        B.Sc in Information Technology
        """

    def test_levenshtein_and_fuzzy_threshold(self):
        # Exact case-insensitive match
        self.assertEqual(normalized_levenshtein("python", "PYTHON"), 1.0)
        # Close match
        self.assertGreaterEqual(normalized_levenshtein("python", "python3"), 0.82)
        # Weak match (should be rejected)
        self.assertLess(normalized_levenshtein("python", "java"), 0.82)

    def test_skill_aliases(self):
        jd_skills = ["JavaScript", "PostgreSQL", "Kubernetes"]
        cand_skills = ["JS", "Postgres", "K8s"]
        matches = MatchFeatures.match_skills(jd_skills, cand_skills, cand_skills)

        matched_types = [m.match_type for m in matches]
        self.assertTrue(all(mt == "Alias" for mt in matched_types))
        self.assertEqual(len(matches), 3)

    def test_empty_jd_and_resume(self):
        result = JDMatcher.match("", "")
        self.assertEqual(result.overall_match_score, 0.0)

    def test_missing_experience_and_education(self):
        minimal_resume = "John Doe. Software developer."
        result = JDMatcher.match(minimal_resume, self.sample_jd)

        exp_comp = next(c for c in result.component_breakdown if c.component_name == "Experience")
        self.assertEqual(exp_comp.status, "Not Determined")

        edu_comp = next(c for c in result.component_breakdown if c.component_name == "Education")
        self.assertEqual(edu_comp.status, "Not Determined")

    def test_full_candidate_matching(self):
        result = JDMatcher.match(self.sample_resume_a, self.sample_jd, candidate_name="Arun Kumar")
        self.assertTrue(result.overall_match_score > 70.0)
        self.assertEqual(result.candidate_name, "Arun Kumar")

        req_skills_comp = next(c for c in result.component_breakdown if c.component_name == "Required Skills")
        self.assertEqual(req_skills_comp.status, "Meets requirement")

    def test_candidate_ranking(self):
        candidates = [
            ("Bala Raju", self.sample_resume_b),
            ("Arun Kumar", self.sample_resume_a)
        ]
        ranked = JDMatcher.rank_candidates(candidates, self.sample_jd, include_ai_signals=True)

        self.assertEqual(len(ranked), 2)
        # Candidate A (Arun) should rank #1 strictly based on qualification match score
        self.assertEqual(ranked[0].candidate_name, "Arun Kumar")
        self.assertEqual(ranked[0].rank, 1)
        self.assertGreater(ranked[0].qualification_match_score, ranked[1].qualification_match_score)

        # Verify AI signal is included without affecting ranking
        self.assertIsNotNone(ranked[0].ai_likelihood_score)

    def test_combined_verification(self):
        combined = JDMatcher.combined_verification(self.sample_resume_a, self.sample_jd, candidate_name="Arun Kumar")
        self.assertEqual(combined.candidate_name, "Arun Kumar")
        self.assertTrue(0.0 <= combined.qualification_match_score <= 100.0)
        self.assertTrue(0.0 <= combined.ai_likelihood_score <= 100.0)
        # Verify scores are separate and to_dict is functional
        d = combined.to_dict()
        self.assertIn("qualification_match_score", d)
        self.assertIn("ai_likelihood_score", d)

    def test_deterministic_matching(self):
        result1 = JDMatcher.match(self.sample_resume_a, self.sample_jd)
        result2 = JDMatcher.match(self.sample_resume_a, self.sample_jd)
        self.assertEqual(result1.overall_match_score, result2.overall_match_score)
        self.assertEqual(result1.to_dict(), result2.to_dict())


class TestSkillClassificationRegression(unittest.TestCase):
    """Regression tests for education/generic word misclassification (Stage 3 bug-fix)."""

    def test_education_terms_not_classified_as_skills(self):
        """B.Tech, B.E., M.Tech, MCA etc. must NOT appear in skill match results."""
        from src.jd_matching.features import is_valid_skill
        education_terms = ["B.Tech", "B.E.", "M.Tech", "MCA", "B.Sc", "M.Sc", "PhD", "bachelor", "education"]
        for term in education_terms:
            self.assertFalse(is_valid_skill(term), f"'{term}' should NOT be classified as a valid skill")

    def test_generic_words_not_classified_as_skills(self):
        """Generic words like 'backend', 'technical', 'experience' must NOT become skills."""
        from src.jd_matching.features import is_valid_skill
        generic_words = ["backend", "technical", "experience", "responsibilities",
                         "qualification", "candidate", "requirements", "title",
                         "skills", "years", "field", "minimum", "preferred", "required"]
        for word in generic_words:
            self.assertFalse(is_valid_skill(word), f"'{word}' should NOT be classified as a valid skill")

    def test_valid_skills_accepted(self):
        """Real technical skills must be correctly accepted."""
        from src.jd_matching.features import is_valid_skill
        valid_skills = ["Java", "Python", "SQL", "Docker", "Spring Boot", "React",
                        "PostgreSQL", "Kubernetes", "AWS", "JavaScript", "Git", "Linux"]
        for skill in valid_skills:
            self.assertTrue(is_valid_skill(skill), f"'{skill}' SHOULD be classified as a valid skill")

    def test_extract_skills_filters_education(self):
        """extract_skills_from_text must not return education terms as skills."""
        text = "Python, Java, B.Tech, Docker, M.Tech, SQL"
        skills = MatchFeatures.extract_skills_from_text(text)
        skills_lower = [s.lower() for s in skills]
        self.assertIn("python", skills_lower)
        self.assertIn("java", skills_lower)
        self.assertIn("docker", skills_lower)
        self.assertIn("sql", skills_lower)
        self.assertNotIn("b.tech", skills_lower)
        self.assertNotIn("m.tech", skills_lower)

    def test_btech_in_jd_qualification_section(self):
        """B.Tech in a qualification section must be handled by education, not skills."""
        jd_text = """
        TECHNICAL SKILLS:
        Java, Spring Boot, SQL, Docker

        QUALIFICATIONS:
        B.Tech or B.E. in Computer Science

        EXPERIENCE:
        2+ years
        """
        resume_text = """
        TECHNICAL SKILLS:
        Java, Spring Boot, SQL, Docker

        EDUCATION:
        B.Tech in Computer Science, 2021
        """
        result = JDMatcher.match(resume_text, jd_text, candidate_name="TestCandidate")

        # Skills component should only contain real skills, not B.Tech
        req_skills = next(c for c in result.component_breakdown if c.component_name == "Required Skills")
        for item in req_skills.matched_items + req_skills.missing_items:
            self.assertNotIn("b.tech", item.lower(), f"Education term 'B.Tech' leaked into skill match: {item}")
            self.assertNotIn("b.e.", item.lower(), f"Education term 'B.E.' leaked into skill match: {item}")

        # Education should properly detect the degree
        edu_comp = next(c for c in result.component_breakdown if c.component_name == "Education")
        self.assertIn(edu_comp.status, ["Meets requirement", "Partially meets"])

    def test_mixed_education_and_skills_jd(self):
        """A JD with both technical skills and education requirements must classify each correctly."""
        jd_text = """
        TECHNICAL SKILLS:
        Python, PostgreSQL, Docker, Kubernetes, JavaScript

        EDUCATION:
        B.Tech or B.E. in Computer Science

        EXPERIENCE:
        3+ years
        """
        resume_text = """
        TECHNICAL SKILLS:
        Python, Postgres, Docker, K8s, JS

        EDUCATION:
        B.Tech in CS, 2020

        EXPERIENCE:
        4 years of experience
        """
        result = JDMatcher.match(resume_text, jd_text, candidate_name="MixedTest")

        # Verify skill matches contain only real technical skills
        for sm in result.skill_matches:
            self.assertNotIn(sm.jd_skill.lower(), ["b.tech", "b.e.", "education", "experience", "years", "technical"])

        self.assertTrue(result.overall_match_score > 50.0)

    def test_no_generic_words_in_skill_matches(self):
        """Skill match results must not contain generic structural words."""
        jd_text = """
        TECHNICAL SKILLS:
        Python, SQL, Docker

        EXPERIENCE:
        2 years
        """
        resume_text = """
        TECHNICAL SKILLS:
        Python, SQL, Docker

        EXPERIENCE:
        3 years of experience
        """
        result = JDMatcher.match(resume_text, jd_text, candidate_name="GenericTest")
        generic_leaks = {"experience", "years", "technical", "skills", "title", "backend", "requirements"}
        for sm in result.skill_matches:
            self.assertNotIn(sm.jd_skill.lower(), generic_leaks,
                             f"Generic word '{sm.jd_skill}' leaked into skill matches")


if __name__ == "__main__":
    unittest.main()


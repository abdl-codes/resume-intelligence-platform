"""
Scoring Improvement Tests (Fix #1 through #8)
Tests cover all 8 required test scenarios as specified in the audit.

Pure Python Standard Library unittest framework.
"""
import unittest
import sys
import os

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.jd_matching.matcher import JDMatcher
from src.jd_matching.features import (
    MatchFeatures, is_valid_skill, strip_resume_header,
    GENERIC_NON_SKILL_WORDS, KEYWORD_GENERIC_WORDS
)
from src.jd_matching.scoring import ScoringEngine
from src.core.section_parser import SectionParser


# ===========================================================================
# Test 1: JD with ALL components present
# ===========================================================================
class TestAllComponentsPresent(unittest.TestCase):
    """
    Test 1: JD with required skills + experience + education + certifications.
    Verifies all components are active and score correctly.
    """

    def setUp(self):
        self.jd = """
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

        self.resume = """
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

    def test_all_components_active(self):
        result = JDMatcher.match(self.resume, self.jd, candidate_name="Arun Kumar")
        active_components = [c for c in result.component_breakdown if c.is_active]

        # Required Skills, Experience, Education, Certifications, Keyword Relevance should all be active
        active_names = {c.component_name for c in active_components}
        self.assertIn("Required Skills", active_names)
        self.assertIn("Experience", active_names)
        self.assertIn("Education", active_names)
        self.assertIn("Certifications", active_names)
        self.assertIn("Keyword Relevance", active_names)

    def test_score_in_valid_range(self):
        result = JDMatcher.match(self.resume, self.jd, candidate_name="Arun Kumar")
        self.assertGreaterEqual(result.overall_match_score, 0.0)
        self.assertLessEqual(result.overall_match_score, 100.0)

    def test_good_candidate_scores_well(self):
        result = JDMatcher.match(self.resume, self.jd, candidate_name="Arun Kumar")
        self.assertGreater(result.overall_match_score, 50.0)

    def test_component_breakdown_has_explanation(self):
        result = JDMatcher.match(self.resume, self.jd, candidate_name="Arun Kumar")
        for comp in result.component_breakdown:
            self.assertTrue(len(comp.explanation) > 0, f"{comp.component_name} missing explanation")


# ===========================================================================
# Test 2: JD with NO certifications
# ===========================================================================
class TestNoCertifications(unittest.TestCase):
    """
    Test 2: JD with NO certifications.
    Verify candidates do NOT receive free certification points.
    """

    def setUp(self):
        self.jd_no_certs = """
        Job Title: Backend Developer

        TECHNICAL SKILLS:
        Python, PostgreSQL, Docker

        EXPERIENCE:
        2+ years of experience

        EDUCATION:
        B.Tech or B.E.
        """

        self.resume = """
        Dev Kumar
        dev@example.com

        TECHNICAL SKILLS:
        Python, PostgreSQL, Docker

        WORK EXPERIENCE:
        Developer (2021 - 2024) - 3 years

        EDUCATION:
        B.Tech in CS, 2021
        """

    def test_certifications_not_active(self):
        result = JDMatcher.match(self.resume, self.jd_no_certs)
        cert_comp = next(c for c in result.component_breakdown if c.component_name == "Certifications")
        self.assertFalse(cert_comp.is_active,
                         "Certifications should NOT be active when JD has no cert requirements")

    def test_no_free_certification_points(self):
        result = JDMatcher.match(self.resume, self.jd_no_certs)
        cert_comp = next(c for c in result.component_breakdown if c.component_name == "Certifications")
        self.assertEqual(cert_comp.normalized_score, 0.0,
                         "Certification score should be 0 (not 100) when JD has no cert requirements")
        self.assertEqual(cert_comp.contribution, 0.0,
                         "Certification contribution should be 0 when JD has no cert requirements")

    def test_score_still_valid_without_certs(self):
        result = JDMatcher.match(self.resume, self.jd_no_certs)
        self.assertGreaterEqual(result.overall_match_score, 0.0)
        self.assertLessEqual(result.overall_match_score, 100.0)
        # A good candidate should still score well even without certs component
        self.assertGreater(result.overall_match_score, 40.0)


# ===========================================================================
# Test 3: JD with NO preferred skills
# ===========================================================================
class TestNoPreferredSkills(unittest.TestCase):
    """
    Test 3: JD with NO preferred skills.
    Verify candidates do NOT automatically receive 100% preferred-skill points.
    """

    def setUp(self):
        self.jd_no_preferred = """
        Job Title: Backend Developer

        TECHNICAL SKILLS:
        Python, Docker, PostgreSQL

        EXPERIENCE:
        2+ years
        """

        self.resume = """
        Test Candidate
        test@email.com

        TECHNICAL SKILLS:
        Python, Docker, PostgreSQL

        WORK EXPERIENCE:
        Developer (2022-2024)
        """

    def test_preferred_skills_not_active(self):
        result = JDMatcher.match(self.resume, self.jd_no_preferred)
        pref_comp = next(c for c in result.component_breakdown if c.component_name == "Preferred Skills")
        self.assertFalse(pref_comp.is_active,
                         "Preferred Skills should NOT be active when JD has none")

    def test_no_automatic_100_percent(self):
        result = JDMatcher.match(self.resume, self.jd_no_preferred)
        pref_comp = next(c for c in result.component_breakdown if c.component_name == "Preferred Skills")
        self.assertEqual(pref_comp.normalized_score, 0.0,
                         "Preferred Skills score should be 0, NOT 100, when JD has none")
        self.assertEqual(pref_comp.contribution, 0.0,
                         "Preferred Skills contribution should be 0 when JD has none")

    def test_jd_with_preferred_skills_section(self):
        """Verify preferred skills ARE extracted when the JD includes them."""
        jd_with_preferred = """
        Job Title: Backend Developer

        TECHNICAL SKILLS:
        Python, Docker, PostgreSQL

        Nice to Have:
        Redis, Elasticsearch, GraphQL

        EXPERIENCE:
        2+ years
        """
        resume = """
        Test Candidate
        test@email.com

        TECHNICAL SKILLS:
        Python, Docker, PostgreSQL, Redis

        WORK EXPERIENCE:
        Developer (2022-2024)
        """
        result = JDMatcher.match(resume, jd_with_preferred)
        pref_comp = next(c for c in result.component_breakdown if c.component_name == "Preferred Skills")
        # Should be active because JD has preferred skills
        self.assertTrue(pref_comp.is_active,
                        "Preferred Skills should be active when JD has a 'Nice to Have' section")
        self.assertGreater(pref_comp.normalized_score, 0.0,
                           "Should have some match score since resume has Redis")


# ===========================================================================
# Test 4: Corporate filler words NOT extracted as skills
# ===========================================================================
class TestCorporateFillerExclusion(unittest.TestCase):
    """
    Test 4: JD containing words like "must", "will", "looking", "offers",
    "strong", "technology". Verify these are NOT extracted as technical skills.
    """

    def test_filler_words_not_valid_skills(self):
        filler_words = [
            "must", "will", "looking", "offers", "strong", "technology",
            "demonstrated", "hands-on", "ensure", "responsible", "ability",
            "work", "team", "candidate", "role", "position", "experience",
            "knowledge", "excellent", "good", "required", "preferred"
        ]
        for word in filler_words:
            self.assertFalse(is_valid_skill(word),
                             f"'{word}' should NOT be classified as a valid skill")

    def test_filler_words_in_generic_set(self):
        """Confirm all requested filler words are in the GENERIC_NON_SKILL_WORDS set."""
        must_have = {"must", "will", "looking", "offers", "along", "technology",
                     "strong", "demonstrated", "ensure", "responsible", "ability",
                     "work", "team", "candidate", "role", "position", "experience",
                     "knowledge", "excellent", "good", "required", "preferred"}
        for word in must_have:
            self.assertIn(word, GENERIC_NON_SKILL_WORDS,
                          f"'{word}' should be in GENERIC_NON_SKILL_WORDS")

    def test_filler_words_not_extracted_from_jd(self):
        """Extract skills from a JD with filler + real skills and verify only real skills come through."""
        text = "must have strong Python experience, will be looking for candidates with Docker and technology knowledge"
        skills = MatchFeatures.extract_skills_from_text(text)
        skills_lower = [s.lower() for s in skills]

        # Real skills should be present
        self.assertIn("python", skills_lower)
        self.assertIn("docker", skills_lower)

        # Filler words should NOT be present
        for filler in ["must", "strong", "looking", "technology", "knowledge", "candidates"]:
            self.assertNotIn(filler, skills_lower,
                             f"Filler word '{filler}' should not be extracted as a skill")


# ===========================================================================
# Test 5: Header/Name leakage prevention
# ===========================================================================
class TestHeaderLeakagePrevention(unittest.TestCase):
    """
    Test 5: Candidate name/email contains a JD keyword.
    Verify the header does NOT artificially increase keyword relevance.
    """

    def test_name_keyword_does_not_inflate_score(self):
        """
        Resume candidate name is 'Java Python' — a name that matches JD keywords.
        Keyword relevance should NOT be inflated by the name match.
        """
        jd = """
        TECHNICAL SKILLS:
        Java, Python, SQL, Docker

        EXPERIENCE:
        2+ years
        """

        # Resume where name contains JD keywords, but body has NO matching skills
        resume_with_keyword_name = """
        Java Python
        java.python@example.com

        WORK EXPERIENCE:
        Marketing assistant at Corp Inc (2022-2024)
        - Managed social media campaigns
        - Created marketing materials

        EDUCATION:
        B.A. in Marketing
        """

        # Resume with normal name and NO matching skills
        resume_normal_name = """
        John Smith
        john.smith@example.com

        WORK EXPERIENCE:
        Marketing assistant at Corp Inc (2022-2024)
        - Managed social media campaigns
        - Created marketing materials

        EDUCATION:
        B.A. in Marketing
        """

        result_keyword_name = JDMatcher.match(resume_with_keyword_name, jd)
        result_normal_name = JDMatcher.match(resume_normal_name, jd)

        kw_score_keyword_name = next(
            c for c in result_keyword_name.component_breakdown
            if c.component_name == "Keyword Relevance"
        ).normalized_score

        kw_score_normal_name = next(
            c for c in result_normal_name.component_breakdown
            if c.component_name == "Keyword Relevance"
        ).normalized_score

        # The keyword-name resume should NOT score significantly higher
        # (allow small tolerance for other text overlap)
        self.assertAlmostEqual(kw_score_keyword_name, kw_score_normal_name, delta=15.0,
                               msg="Name containing JD keywords should not significantly inflate keyword relevance")

    def test_strip_resume_header(self):
        """Verify the strip_resume_header utility works correctly."""
        resume_text = """
        Java Python
        java.python@example.com
        +1-555-123-4567

        TECHNICAL SKILLS:
        React, Node.js

        WORK EXPERIENCE:
        Developer at company
        """
        resume_doc = SectionParser.parse_resume(resume_text)
        body = strip_resume_header(resume_doc)

        # Name should not be in body
        self.assertNotIn("Java Python", body,
                         "Candidate name should be stripped from body text")
        # Email should not be in body
        self.assertNotIn("java.python@example.com", body,
                         "Email should be stripped from body text")
        # Skills should still be in body
        self.assertIn("React", body)


# ===========================================================================
# Test 6: Legitimate technical terms preserved
# ===========================================================================
class TestTechnicalTermsPreserved(unittest.TestCase):
    """
    Test 6: JD contains technical terms like Python, Java, SQL, Docker, 
    Kubernetes, AWS, Spring Boot. Verify they are still extracted.
    """

    def test_technical_skills_are_valid(self):
        technical_skills = [
            "Python", "Java", "SQL", "Docker", "Kubernetes", "AWS",
            "Spring Boot", "React", "PostgreSQL", "JavaScript", "Git",
            "Linux", "MongoDB", "Redis", "Kafka", "GraphQL"
        ]
        for skill in technical_skills:
            self.assertTrue(is_valid_skill(skill),
                            f"'{skill}' SHOULD be classified as a valid skill")

    def test_technical_skills_extracted_from_jd(self):
        text = "Python, Java, SQL, Docker, Kubernetes, AWS, Spring Boot"
        skills = MatchFeatures.extract_skills_from_text(text)
        skills_lower = [s.lower() for s in skills]

        for expected in ["python", "java", "sql", "docker", "kubernetes", "aws", "spring boot"]:
            self.assertIn(expected, skills_lower,
                          f"Technical skill '{expected}' should be extracted from JD text")

    def test_technical_skills_matched_in_scoring(self):
        jd = """
        TECHNICAL SKILLS:
        Python, Java, SQL, Docker, Kubernetes, AWS, Spring Boot
        """
        resume = """
        TECHNICAL SKILLS:
        Python, Java, SQL, Docker, K8s, AWS, Spring

        WORK EXPERIENCE:
        Developer 2020-2024
        """
        result = JDMatcher.match(resume, jd)
        req_comp = next(c for c in result.component_breakdown if c.component_name == "Required Skills")
        self.assertGreater(req_comp.normalized_score, 50.0,
                           "Matching technical skills should yield a good score")


# ===========================================================================
# Test 7: Final score always 0–100
# ===========================================================================
class TestFinalScoreRange(unittest.TestCase):
    """
    Test 7: Verify final score is always between 0 and 100.
    """

    def test_perfect_match_capped_at_100(self):
        jd = """
        TECHNICAL SKILLS:
        Python

        EXPERIENCE:
        1+ years
        """
        resume = """
        TECHNICAL SKILLS:
        Python

        EXPERIENCE:
        5 years of experience with Python
        """
        result = JDMatcher.match(resume, jd)
        self.assertLessEqual(result.overall_match_score, 100.0)
        self.assertGreaterEqual(result.overall_match_score, 0.0)

    def test_no_match_at_least_zero(self):
        jd = """
        TECHNICAL SKILLS:
        Haskell, Erlang, Scala, Clojure

        EXPERIENCE:
        10+ years

        CERTIFICATIONS:
        PMP, CISSP
        """
        resume = """
        Marketing Intern
        - Made coffee
        - Organized files
        """
        result = JDMatcher.match(resume, jd)
        self.assertGreaterEqual(result.overall_match_score, 0.0)
        self.assertLessEqual(result.overall_match_score, 100.0)

    def test_empty_jd_zero_score(self):
        result = JDMatcher.match("Some resume text here", "")
        self.assertEqual(result.overall_match_score, 0.0)

    def test_empty_resume_zero_score(self):
        result = JDMatcher.match("", "Some JD text here with Python requirements")
        self.assertEqual(result.overall_match_score, 0.0)

    def test_various_jd_shapes(self):
        """Test many different JD shapes to ensure score is always in range."""
        jds = [
            # Only skills
            "TECHNICAL SKILLS: Python, Java, SQL",
            # Skills + experience
            "TECHNICAL SKILLS: Python\nEXPERIENCE: 5+ years",
            # Very sparse JD
            "We need a developer",
            # Full JD
            """TECHNICAL SKILLS: Python, Java
            EXPERIENCE: 3+ years
            EDUCATION: B.Tech
            CERTIFICATIONS: AWS""",
        ]
        resume = """
        Test Candidate
        TECHNICAL SKILLS: Python, React
        EXPERIENCE: 2 years
        EDUCATION: B.Tech in CS
        """
        for jd in jds:
            result = JDMatcher.match(resume, jd)
            self.assertGreaterEqual(result.overall_match_score, 0.0,
                                    f"Score below 0 for JD: {jd[:50]}")
            self.assertLessEqual(result.overall_match_score, 100.0,
                                 f"Score above 100 for JD: {jd[:50]}")


# ===========================================================================
# Test 8: All candidates use same scoring rules
# ===========================================================================
class TestConsistentScoringRules(unittest.TestCase):
    """
    Test 8: Verify all candidates are evaluated using exactly the same scoring rules.
    """

    def setUp(self):
        self.jd = """
        TECHNICAL SKILLS:
        Python, Docker, SQL

        EXPERIENCE:
        3+ years

        EDUCATION:
        B.Tech

        CERTIFICATIONS:
        AWS
        """

    def test_same_resume_same_score(self):
        """Identical resumes must produce identical scores."""
        resume = """
        TECHNICAL SKILLS: Python, Docker, SQL
        EXPERIENCE: 3 years
        EDUCATION: B.Tech
        CERTIFICATIONS: AWS
        """
        result1 = JDMatcher.match(resume, self.jd, candidate_name="Alice")
        result2 = JDMatcher.match(resume, self.jd, candidate_name="Bob")
        self.assertAlmostEqual(result1.overall_match_score, result2.overall_match_score, places=2)

    def test_deterministic_scoring(self):
        """Same resume run twice should produce identical scores."""
        resume = """
        TECHNICAL SKILLS: Python, Docker
        EXPERIENCE: 2 years
        """
        result1 = JDMatcher.match(resume, self.jd)
        result2 = JDMatcher.match(resume, self.jd)
        self.assertEqual(result1.overall_match_score, result2.overall_match_score)

    def test_active_weights_consistent(self):
        """All candidates should have the same set of active/inactive components for the same JD."""
        resumes = [
            ("Candidate A", "TECHNICAL SKILLS: Python, Docker, SQL\nEXPERIENCE: 5 years\nEDUCATION: B.Tech\nCERTIFICATIONS: AWS"),
            ("Candidate B", "TECHNICAL SKILLS: Java, React\nEXPERIENCE: 1 year"),
            ("Candidate C", "Marketing Manager\nManaged campaigns"),
        ]
        active_sets = []
        for name, resume in resumes:
            result = JDMatcher.match(resume, self.jd, candidate_name=name)
            active_names = tuple(sorted(c.component_name for c in result.component_breakdown if c.is_active))
            active_sets.append(active_names)

        # All candidates should have the same active component set (determined by JD, not resume)
        for i in range(1, len(active_sets)):
            self.assertEqual(active_sets[0], active_sets[i],
                             "All candidates should have the same active components for the same JD")

    def test_ranking_consistent(self):
        """Ranking must use the same scoring rules for all candidates."""
        from src.jd_matching.matcher import JDMatcher

        candidates = [
            ("Weak", "Marketing intern"),
            ("Strong", "TECHNICAL SKILLS: Python, Docker, SQL\nEXPERIENCE: 5 years\nEDUCATION: B.Tech\nCERTIFICATIONS: AWS"),
        ]
        ranked = JDMatcher.rank_candidates(candidates, self.jd, include_ai_signals=False)
        self.assertEqual(ranked[0].candidate_name, "Strong")
        self.assertEqual(ranked[1].candidate_name, "Weak")


# ===========================================================================
# Additional: Dynamic Weight Normalization
# ===========================================================================
class TestDynamicWeightNormalization(unittest.TestCase):
    """
    Tests for the dynamic weight normalization formula (Fix #6).
    """

    def test_formula_with_all_active(self):
        """When all components are active, the formula should match a simple weighted sum."""
        from src.jd_matching.models import ComponentMatchResult

        components = [
            ComponentMatchResult("A", 80.0, 80.0, 0.40, 32.0, "OK", is_active=True),
            ComponentMatchResult("B", 60.0, 60.0, 0.30, 18.0, "OK", is_active=True),
            ComponentMatchResult("C", 100.0, 100.0, 0.30, 30.0, "OK", is_active=True),
        ]
        score = ScoringEngine.compute_dynamic_final_score(components)
        expected = (80.0 * 0.40 + 60.0 * 0.30 + 100.0 * 0.30) / (0.40 + 0.30 + 0.30)
        self.assertAlmostEqual(score, expected, places=2)

    def test_formula_with_inactive_component(self):
        """Inactive components should be excluded from both numerator and denominator."""
        from src.jd_matching.models import ComponentMatchResult

        components = [
            ComponentMatchResult("A", 80.0, 80.0, 0.40, 32.0, "OK", is_active=True),
            ComponentMatchResult("B", 0.0, 0.0, 0.30, 0.0, "N/A", is_active=False),  # inactive
            ComponentMatchResult("C", 100.0, 100.0, 0.30, 30.0, "OK", is_active=True),
        ]
        score = ScoringEngine.compute_dynamic_final_score(components)
        expected = (80.0 * 0.40 + 100.0 * 0.30) / (0.40 + 0.30)
        self.assertAlmostEqual(score, expected, places=2)

    def test_formula_all_inactive(self):
        """If all components are inactive, score should be 0."""
        from src.jd_matching.models import ComponentMatchResult

        components = [
            ComponentMatchResult("A", 0.0, 0.0, 0.50, 0.0, "N/A", is_active=False),
            ComponentMatchResult("B", 0.0, 0.0, 0.50, 0.0, "N/A", is_active=False),
        ]
        score = ScoringEngine.compute_dynamic_final_score(components)
        self.assertEqual(score, 0.0)

    def test_score_clamped_to_100(self):
        """Score should never exceed 100."""
        from src.jd_matching.models import ComponentMatchResult

        components = [
            ComponentMatchResult("A", 100.0, 100.0, 0.50, 50.0, "OK", is_active=True),
            ComponentMatchResult("B", 100.0, 100.0, 0.50, 50.0, "OK", is_active=True),
        ]
        score = ScoringEngine.compute_dynamic_final_score(components)
        self.assertLessEqual(score, 100.0)


# ===========================================================================
# Additional: Preferred Skills Extraction
# ===========================================================================
class TestPreferredSkillsExtraction(unittest.TestCase):
    """Tests for preferred skills extraction from JD (Fix #1)."""

    def test_extract_from_nice_to_have_section(self):
        jd_text = """
        TECHNICAL SKILLS:
        Python, Docker

        Nice to Have:
        Redis, Elasticsearch, GraphQL
        """
        jd_doc = SectionParser.parse_job_description(jd_text)
        prefs = MatchFeatures.extract_preferred_skills_from_jd(jd_doc)
        prefs_lower = [p.lower() for p in prefs]
        self.assertTrue(len(prefs) > 0, "Should extract preferred skills from 'Nice to Have' section")

    def test_extract_from_preferred_skills_section(self):
        jd_text = """
        TECHNICAL SKILLS:
        Python, Docker

        Preferred Skills:
        Redis, Kafka, AWS
        """
        jd_doc = SectionParser.parse_job_description(jd_text)
        prefs = MatchFeatures.extract_preferred_skills_from_jd(jd_doc)
        self.assertTrue(len(prefs) > 0, "Should extract preferred skills from 'Preferred Skills' section")

    def test_no_preferred_returns_empty(self):
        jd_text = """
        TECHNICAL SKILLS:
        Python, Docker

        EXPERIENCE:
        2+ years
        """
        jd_doc = SectionParser.parse_job_description(jd_text)
        prefs = MatchFeatures.extract_preferred_skills_from_jd(jd_doc)
        self.assertEqual(len(prefs), 0, "Should return empty list when no preferred skills section exists")


# ===========================================================================
# Additional: Explanation Data (Fix #8)
# ===========================================================================
class TestExplanationData(unittest.TestCase):
    """Test 8 (Explanation Data): Verify all explanation fields are present."""

    def test_all_explanation_fields_present(self):
        jd = """
        TECHNICAL SKILLS:
        Python, Docker, SQL

        Nice to Have:
        Redis

        EXPERIENCE:
        3+ years

        EDUCATION:
        B.Tech

        CERTIFICATIONS:
        AWS
        """
        resume = """
        Test Candidate
        test@example.com

        TECHNICAL SKILLS:
        Python, Docker

        WORK EXPERIENCE:
        Developer (2020-2024)

        EDUCATION:
        B.Tech in CS

        CERTIFICATIONS:
        AWS
        """
        result = JDMatcher.match(resume, jd)
        result_dict = result.to_dict()

        # Verify component breakdown has all expected fields
        for comp in result_dict["component_breakdown"]:
            self.assertIn("component_name", comp)
            self.assertIn("normalized_score", comp)
            self.assertIn("weight", comp)
            self.assertIn("contribution", comp)
            self.assertIn("status", comp)
            self.assertIn("is_active", comp)
            self.assertIn("matched_items", comp)
            self.assertIn("missing_items", comp)
            self.assertIn("explanation", comp)

        # Verify skill matches have all expected fields
        for sm in result_dict["skill_matches"]:
            self.assertIn("jd_skill", sm)
            self.assertIn("resume_skill", sm)
            self.assertIn("similarity_score", sm)
            self.assertIn("match_type", sm)

        # Verify overall score is present
        self.assertIn("overall_match_score", result_dict)
        self.assertIn("candidate_name", result_dict)

    def test_component_names_cover_all_areas(self):
        jd = """
        TECHNICAL SKILLS: Python
        Nice to Have: Redis
        EXPERIENCE: 2+ years
        EDUCATION: B.Tech
        CERTIFICATIONS: AWS
        """
        resume = """
        TECHNICAL SKILLS: Python
        EXPERIENCE: 3 years
        EDUCATION: B.Tech
        CERTIFICATIONS: AWS
        """
        result = JDMatcher.match(resume, jd)
        comp_names = {c.component_name for c in result.component_breakdown}

        self.assertIn("Required Skills", comp_names)
        self.assertIn("Preferred Skills", comp_names)
        self.assertIn("Experience", comp_names)
        self.assertIn("Education", comp_names)
        self.assertIn("Certifications", comp_names)
        self.assertIn("Keyword Relevance", comp_names)


# ===========================================================================
# Additional: Keyword Relevance Rarity Weighting (Fix #5)
# ===========================================================================
class TestKeywordRarityWeighting(unittest.TestCase):
    """Tests for keyword rarity/importance weighting (Fix #5)."""

    def test_generic_words_lower_weight(self):
        from src.jd_matching.features import compute_keyword_rarity_weights
        jd_tokens = {"python", "team", "work", "docker", "strong"}
        weights = compute_keyword_rarity_weights(jd_tokens, set())

        # Technical terms should have higher weight than generic words
        self.assertGreater(weights["python"], weights["team"])
        self.assertGreater(weights["docker"], weights["strong"])
        self.assertGreater(weights["python"], weights["work"])

    def test_technical_terms_higher_weight(self):
        from src.jd_matching.features import compute_keyword_rarity_weights
        jd_tokens = {"python", "sql", "aws", "team", "experience"}
        weights = compute_keyword_rarity_weights(jd_tokens, set())

        for tech in ["python", "sql", "aws"]:
            for generic in ["team", "experience"]:
                self.assertGreater(weights[tech], weights[generic],
                                   f"Technical term '{tech}' should have higher weight than generic '{generic}'")


if __name__ == "__main__":
    unittest.main()

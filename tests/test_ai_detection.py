"""
Unit Tests for Stage 2: Resume AI-Generated Likelihood Detection Engine
Pure Python Standard Library unittest framework.
"""
import unittest
from src.ai_detection import AIDetector, AIDetectionResult, FeatureExtractor


class TestAIDetector(unittest.TestCase):

    def test_empty_text(self):
        result = AIDetector.analyze("")
        self.assertEqual(result.ai_likelihood_score, 0.0)
        self.assertEqual(result.confidence, "Low")
        self.assertEqual(result.category, "Low AI-style signals")
        self.assertTrue(len(result.signals) > 0)

    def test_very_short_text(self):
        text = "John Doe. Software Developer."
        result = AIDetector.analyze(text)
        self.assertTrue(0.0 <= result.ai_likelihood_score <= 100.0)
        self.assertEqual(result.confidence, "Low")

    def test_normal_human_sample(self):
        human_text = """
        John Smith
        john@example.com | (555) 123-4567

        WORK EXPERIENCE:
        Software Engineer at Acme Corp (2020 - Present)
        - Wrote Python backend APIs for user authentication.
        - Fixed bugs in PostgreSQL database connections and reduced query latency.
        - Worked with a small team of 3 developers on sprint tasks.

        EDUCATION:
        BS in Computer Science, State University, 2019
        """
        result = AIDetector.analyze(human_text)
        self.assertTrue(0.0 <= result.ai_likelihood_score <= 100.0)
        self.assertIn(result.category, ["Low AI-style signals", "Moderate AI-style signals"])
        for feature in result.feature_breakdown:
            self.assertTrue(len(feature.explanation) > 0)

    def test_cliche_heavy_text(self):
        cliche_text = """
        Results-driven and highly motivated dynamic professional with a proven track record of success.
        Passionate about leveraging cutting-edge technology to delve into complex problems.
        Strong communication skills and a team player who thinks outside the box.
        Spearheaded pivotal initiatives across a transformative realm to achieve mastery and synergy.
        """
        result = AIDetector.analyze(cliche_text)
        self.assertTrue(result.ai_likelihood_score > 30.0)
        cliche_feature = next(f for f in result.feature_breakdown if f.feature_name == "Generic / Cliché Phrase Density")
        self.assertTrue(cliche_feature.normalized_score > 50.0)

    def test_transition_heavy_text(self):
        transition_text = """
        Additionally, implemented scalable server infrastructure.
        Furthermore, optimized SQL queries to reduce latency.
        Moreover, led sprint planning meetings with cross-functional teams.
        In addition, designed RESTful APIs using Python and Docker.
        """
        result = AIDetector.analyze(transition_text)
        transition_feature = next(f for f in result.feature_breakdown if f.feature_name == "Transition Phrase Density")
        self.assertTrue(transition_feature.normalized_score > 50.0)

    def test_highly_repetitive_text(self):
        repetitive_text = """
        Managed software development projects for enterprise clients.
        Managed software development projects for enterprise clients.
        Managed software development projects for enterprise clients.
        """
        result = AIDetector.analyze(repetitive_text)
        rep_feature = next(f for f in result.feature_breakdown if f.feature_name == "Repetition Index")
        self.assertTrue(rep_feature.normalized_score > 0.0)

    def test_low_lexical_diversity(self):
        low_div_text = "test test test test test test test test test test"
        result = AIDetector.analyze(low_div_text)
        lex_feature = next(f for f in result.feature_breakdown if f.feature_name == "Lexical Diversity")
        self.assertEqual(lex_feature.normalized_score, 100.0)

    def test_mixed_content_resume(self):
        mixed_resume = """
        Jane Doe - Senior Full Stack Engineer
        jane.doe@email.com | github.com/janedoe

        SUMMARY:
        Results-driven and highly motivated engineer with 8 years of experience.

        EXPERIENCE:
        Tech Lead - Cloud Solutions Inc.
        - Built distributed real-time data pipelines processing 1M events/sec.
        - Additionally, introduced automated CI/CD deployment workflows.
        - Managed team of 6 engineers across frontend and backend services.

        SKILLS:
        Python, Go, JavaScript, React, Kubernetes, AWS, SQL
        """
        result = AIDetector.analyze(mixed_resume, file_name="jane_doe_resume.txt")
        self.assertTrue(0.0 <= result.ai_likelihood_score <= 100.0)
        self.assertIn(result.confidence, ["Moderate", "High"])
        self.assertEqual(len(result.feature_breakdown), 7)
        self.assertIsNotNone(result.to_dict())

    def test_deterministic_execution(self):
        sample_text = "Experienced Python developer with a proven track record in software engineering."
        result1 = AIDetector.analyze(sample_text)
        result2 = AIDetector.analyze(sample_text)
        self.assertEqual(result1.ai_likelihood_score, result2.ai_likelihood_score)
        self.assertEqual(result1.category, result2.category)
        self.assertEqual(result1.to_dict(), result2.to_dict())

    def test_score_bounding_and_explanations(self):
        sample_text = "Dynamic and results-driven software engineer."
        result = AIDetector.analyze(sample_text)
        self.assertGreaterEqual(result.ai_likelihood_score, 0.0)
        self.assertLessEqual(result.ai_likelihood_score, 100.0)
        for feature in result.feature_breakdown:
            self.assertGreaterEqual(feature.normalized_score, 0.0)
            self.assertLessEqual(feature.normalized_score, 100.0)
            self.assertIsNotNone(feature.explanation)
            self.assertTrue(len(feature.explanation) > 0)


if __name__ == "__main__":
    unittest.main()

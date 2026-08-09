"""
Unit Tests for Core Processing & Ingestion Engine (Stage 1)
Uses standard library unittest framework.
"""
import unittest
from src.core.models import ParsedSection, ResumeDocument, JobDescription
from src.core.text_processing import (
    tokenize,
    split_sentences,
    remove_stopwords,
    get_ngrams,
    simple_stem
)
from src.core.section_parser import SectionParser


class TestTextProcessing(unittest.TestCase):

    def test_tokenize(self):
        text = "Senior Python Developer with C++ & .NET experience in React.js!"
        tokens = tokenize(text)
        self.assertIn("python", tokens)
        self.assertIn("c++", tokens)
        self.assertIn(".net", tokens)
        self.assertIn("developer", tokens)

    def test_split_sentences(self):
        text = "Experienced software engineer. Led a team of 5 developers! Worked on AI systems."
        sentences = split_sentences(text)
        self.assertEqual(len(sentences), 3)
        self.assertEqual(sentences[0], "Experienced software engineer.")
        self.assertEqual(sentences[1], "Led a team of 5 developers!")

    def test_remove_stopwords(self):
        tokens = ["the", "quick", "brown", "fox", "and", "is"]
        filtered = remove_stopwords(tokens)
        self.assertEqual(filtered, ["quick", "brown", "fox"])

    def test_get_ngrams(self):
        tokens = ["machine", "learning", "engineer"]
        bigrams = get_ngrams(tokens, 2)
        trigrams = get_ngrams(tokens, 3)
        self.assertEqual(bigrams, [("machine", "learning"), ("learning", "engineer")])
        self.assertEqual(trigrams, [("machine", "learning", "engineer")])

    def test_simple_stem(self):
        self.assertEqual(simple_stem("developing"), "develop")
        self.assertEqual(simple_stem("applications"), "applicate")


class TestSectionParser(unittest.TestCase):

    def test_contact_info_extraction(self):
        sample_text = """
        John Doe
        Email: john.doe@example.com
        Phone: (555) 019-2834
        LinkedIn: https://linkedin.com/in/johndoe
        """
        email, phone, links = SectionParser.extract_contact_info(sample_text)
        self.assertEqual(email, "john.doe@example.com")
        self.assertIsNotNone(phone)
        self.assertTrue(any("linkedin.com" in link for link in links))

    def test_section_parsing(self):
        sample_resume = """
        John Doe
        john@example.com

        PROFESSIONAL SUMMARY:
        Resourceful Software Engineer with over 6 years of experience building scalable backend microservices.

        WORK EXPERIENCE:
        - Spearheaded backend microservice architecture using Python and Docker.
        - Improved database query performance by 45%.

        TECHNICAL SKILLS:
        Python, C++, SQL, Docker, Linux, Git

        EDUCATION:
        B.S. in Computer Science - State University
        """
        doc = SectionParser.parse_resume(sample_resume, file_name="john_doe_resume.txt")
        self.assertEqual(doc.contact_email, "john@example.com")
        self.assertTrue(len(doc.sections) >= 3)
        
        exp_section = doc.get_section("experience")
        self.assertIsNotNone(exp_section)
        self.assertTrue(len(exp_section.bullet_points) >= 2)
        
        skills_section = doc.get_section("skills")
        self.assertIsNotNone(skills_section)

    def test_parse_job_description(self):
        sample_jd = """
        Job Title: Senior Backend Engineer
        Company: TechCorp

        Requirements:
        - 5+ years of experience in Python.
        - Experience with PostgreSQL and Docker.
        """
        jd = SectionParser.parse_job_description(sample_jd, title="Senior Backend Engineer", company="TechCorp")
        self.assertEqual(jd.title, "Senior Backend Engineer")
        self.assertTrue(len(jd.tokens) > 0)
        self.assertTrue(len(jd.sentences) > 0)


if __name__ == "__main__":
    unittest.main()

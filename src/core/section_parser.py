"""
Section Parser and Extractor
Parses raw resume and job description text into structured sections, bullet points,
and metadata using standard library regular expressions.
"""
import re
from typing import List, Dict, Tuple, Optional
from .models import ParsedSection, ResumeDocument, JobDescription
from .text_processing import tokenize, split_sentences, remove_stopwords


class SectionParser:
    """
    Standard-library rule-based parser for Resumes and Job Descriptions.
    """
    
    # Common section title header aliases
    SECTION_ALIASES: Dict[str, List[str]] = {
        "summary": [
            "summary", "executive summary", "profile", "objective", "professional summary",
            "about me", "overview", "career objective"
        ],
        "experience": [
            "experience", "work experience", "employment history", "professional experience",
            "work history", "career history", "relevant experience", "employment"
        ],
        "skills": [
            "skills", "technical skills", "core competencies", "technologies", "expertise",
            "skills & tools", "technical proficiencies", "key skills"
        ],
        "education": [
            "education", "academic background", "academic qualifications", "qualifications",
            "education and training", "academic history"
        ],
        "projects": [
            "projects", "key projects", "personal projects", "portfolio", "selected projects"
        ],
        "certifications": [
            "certifications", "licenses", "certificates", "credentials", "training & certifications"
        ]
    }
    
    REGEX_EMAIL = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
    REGEX_PHONE = re.compile(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}')
    REGEX_LINK = re.compile(r'https?://[^\s]+|linkedin\.com/in/[^\s]+|github\.com/[^\s]+')
    
    @classmethod
    def extract_contact_info(cls, text: str) -> Tuple[Optional[str], Optional[str], List[str]]:
        """
        Extracts email, phone, and profile links from text.
        """
        email_match = cls.REGEX_EMAIL.search(text)
        phone_match = cls.REGEX_PHONE.search(text)
        links = cls.REGEX_LINK.findall(text)
        
        email = email_match.group(0) if email_match else None
        phone = phone_match.group(0) if phone_match else None
        
        return email, phone, links

    @classmethod
    def normalize_section_title(cls, header_text: str) -> str:
        """
        Maps a header string to a canonical section name.
        """
        clean_header = header_text.strip().lower()
        clean_header = re.sub(r'[^a-z0-9\s&]', '', clean_header).strip()
        
        for canonical, aliases in cls.SECTION_ALIASES.items():
            for alias in aliases:
                if clean_header == alias or clean_header.startswith(alias):
                    return canonical
                    
        return clean_header if clean_header else "general"

    @classmethod
    def extract_bullet_points(cls, text: str) -> List[str]:
        """
        Extracts bulleted points from section text block.
        """
        lines = text.split('\n')
        bullets = []
        for line in lines:
            stripped = line.strip()
            # Match lines starting with common bullet symbols or numbered lists
            if re.match(r'^[-\*•o>]\s+', stripped) or re.match(r'^\d+[\.\)]\s+', stripped):
                clean_bullet = re.sub(r'^([-\*•o>]\s*|\d+[\.\)]\s*)', '', stripped).strip()
                if clean_bullet:
                    bullets.append(clean_bullet)
        return bullets

    @classmethod
    def parse_resume(cls, text: str, file_name: str = "") -> ResumeDocument:
        """
        Parses raw text into a ResumeDocument with extracted metadata and parsed sections.
        """
        email, phone, links = cls.extract_contact_info(text)
        sections = cls.split_into_sections(text)
        tokens = tokenize(text)
        filtered_tokens = remove_stopwords(tokens)
        sentences = split_sentences(text)
        
        return ResumeDocument(
            raw_text=text,
            file_name=file_name,
            contact_email=email,
            contact_phone=phone,
            links=links,
            sections=sections,
            tokens=tokens,
            filtered_tokens=filtered_tokens,
            sentences=sentences
        )

    @classmethod
    def parse_job_description(cls, text: str, title: str = "", company: str = "") -> JobDescription:
        """
        Parses raw job description text into a JobDescription document.
        """
        sections = cls.split_into_sections(text)
        tokens = tokenize(text)
        filtered_tokens = remove_stopwords(tokens)
        sentences = split_sentences(text)
        
        return JobDescription(
            raw_text=text,
            title=title,
            company=company,
            sections=sections,
            tokens=tokens,
            filtered_tokens=filtered_tokens,
            sentences=sentences
        )

    @classmethod
    def split_into_sections(cls, text: str) -> List[ParsedSection]:
        """
        Splits a text document into logical ParsedSection objects using header detection.
        """
        lines = text.split('\n')
        sections: List[ParsedSection] = []
        
        current_title = "Header"
        current_lines: List[str] = []
        
        # Regex to detect line header candidates (e.g. UPPERCASE, ends with colon, or matches section alias)
        header_candidate_regex = re.compile(
            r'^(?:[A-Z\s&]{3,30}:?|[A-Z][a-z\s&]{2,25}:)$'
        )
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                current_lines.append(line)
                continue
                
            # Check if line looks like a section header
            normalized_candidate = cls.normalize_section_title(stripped)
            is_known_alias = any(
                normalized_candidate == key for key in cls.SECTION_ALIASES.keys()
            )
            is_header_pattern = bool(header_candidate_regex.match(stripped)) and len(stripped.split()) <= 4
            
            if is_known_alias or is_header_pattern:
                # Save previous section if it has content
                raw_section_text = '\n'.join(current_lines).strip()
                if raw_section_text:
                    bullets = cls.extract_bullet_points(raw_section_text)
                    sections.append(ParsedSection(
                        name=current_title,
                        raw_text=raw_section_text,
                        bullet_points=bullets,
                        normalized_title=cls.normalize_section_title(current_title)
                    ))
                
                # Start new section
                current_title = stripped.rstrip(':')
                current_lines = []
            else:
                current_lines.append(line)
                
        # Save last section
        raw_section_text = '\n'.join(current_lines).strip()
        if raw_section_text:
            bullets = cls.extract_bullet_points(raw_section_text)
            sections.append(ParsedSection(
                name=current_title,
                raw_text=raw_section_text,
                bullet_points=bullets,
                normalized_title=cls.normalize_section_title(current_title)
            ))
            
        return sections

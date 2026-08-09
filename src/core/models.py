"""
Core Data Models for Resume and Job Description Documents
Using Python Standard Library dataclasses.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class ParsedSection:
    """
    Represents a categorized section within a Resume or Job Description.
    """
    name: str
    raw_text: str
    bullet_points: List[str] = field(default_factory=list)
    normalized_title: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "normalized_title": self.normalized_title,
            "raw_text": self.raw_text,
            "bullet_points": self.bullet_points,
        }


@dataclass
class ResumeDocument:
    """
    Represents an ingested resume document with extracted metadata and parsed sections.
    """
    raw_text: str
    file_name: str = ""
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    links: List[str] = field(default_factory=list)
    sections: List[ParsedSection] = field(default_factory=list)
    tokens: List[str] = field(default_factory=list)
    filtered_tokens: List[str] = field(default_factory=list)
    sentences: List[str] = field(default_factory=list)

    def get_section(self, section_name: str) -> Optional[ParsedSection]:
        """Finds a section by its normalized name."""
        target = section_name.lower()
        for s in self.sections:
            if s.normalized_title.lower() == target or s.name.lower() == target:
                return s
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_name": self.file_name,
            "contact_email": self.contact_email,
            "contact_phone": self.contact_phone,
            "links": self.links,
            "sections": [s.to_dict() for s in self.sections],
            "total_words": len(self.tokens),
            "total_sentences": len(self.sentences),
        }


@dataclass
class JobDescription:
    """
    Represents an ingested job description document.
    """
    raw_text: str
    title: str = ""
    company: str = ""
    sections: List[ParsedSection] = field(default_factory=list)
    tokens: List[str] = field(default_factory=list)
    filtered_tokens: List[str] = field(default_factory=list)
    sentences: List[str] = field(default_factory=list)

    def get_section(self, section_name: str) -> Optional[ParsedSection]:
        """Finds a section by its normalized name."""
        target = section_name.lower()
        for s in self.sections:
            if s.normalized_title.lower() == target or s.name.lower() == target:
                return s
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "company": self.company,
            "sections": [s.to_dict() for s in self.sections],
            "total_words": len(self.tokens),
            "total_sentences": len(self.sentences),
        }

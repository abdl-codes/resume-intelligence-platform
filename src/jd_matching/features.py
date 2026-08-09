"""
Feature Extractor and Standard Library Skill Matching Utilities
Pure Python Standard Library.
"""
import re
import math
from typing import List, Set, Dict, Tuple, Optional, Any
from src.core.models import ResumeDocument, JobDescription
from src.core.text_processing import tokenize, remove_stopwords
from .models import SkillMatchItem


# Transparent Editable Skill Alias Dictionary
SKILL_ALIASES: Dict[str, Set[str]] = {
    "javascript": {"js", "ecmascript"},
    "js": {"javascript"},
    "typescript": {"ts"},
    "ts": {"typescript"},
    "python": {"py", "python3"},
    "py": {"python", "python3"},
    "python3": {"python"},
    "postgresql": {"postgres", "pgsql"},
    "postgres": {"postgresql", "pgsql"},
    "kubernetes": {"k8s"},
    "k8s": {"kubernetes"},
    "aws": {"amazon web services"},
    "amazon web services": {"aws"},
    "react": {"reactjs", "react.js"},
    "reactjs": {"react", "react.js"},
    "node": {"nodejs", "node.js"},
    "nodejs": {"node", "node.js"},
    "docker": {"containerization"},
    "c++": {"cpp"},
    "cpp": {"c++"},
    "c#": {"csharp", ".net"},
    "csharp": {"c#"},
    "spring boot": {"spring"},
    "spring": {"spring boot"}
}

# Standardized Education Degree Normalizations
EDUCATION_DEGREES: Dict[str, List[str]] = {
    "b.tech": ["btech", "b.tech", "bachelor of technology", "b.e", "be", "bachelor of engineering", "bachelor"],
    "b.e.": ["be", "b.e.", "bachelor of engineering", "btech", "b.tech"],
    "m.tech": ["mtech", "m.tech", "master of technology", "m.e", "me", "master of engineering", "master"],
    "mca": ["mca", "master of computer applications"],
    "b.sc": ["bsc", "b.sc", "bachelor of science"],
    "m.sc": ["msc", "m.sc", "master of science"],
    "phd": ["doctorate", "phd", "ph.d."]
}

# Set of Generic Domain / Structural Words that MUST NOT be classified as skills
# Expanded with common corporate filler language (Fix #3)
GENERIC_NON_SKILL_WORDS: Set[str] = {
    "backend", "frontend", "fullstack", "technical", "experience", "responsibilities",
    "responsibility", "qualification", "qualifications", "candidate", "requirements",
    "requirement", "title", "skills", "years", "job", "company", "role", "work",
    "overview", "summary", "description", "details", "minimum", "preferred", "required",
    "field", "industry", "team", "working", "ability", "knowledge", "strong", "good",
    "excellent", "proficient", "position", "relevant", "heading", "header", "profile",
    # --- Expanded corporate filler words (Fix #3) ---
    "must", "will", "looking", "offers", "along", "technology", "demonstrated",
    "hands-on", "ensure", "responsible", "candidate", "knowledge", "excellent",
    "required", "preferred", "using", "including", "understanding", "environment",
    "develop", "developing", "development", "design", "designing", "building",
    "build", "implement", "implementing", "implementation", "manage", "managing",
    "management", "support", "supporting", "maintain", "maintaining", "create",
    "creating", "provide", "providing", "collaborate", "collaborating", "lead",
    "leading", "deliver", "delivering", "drive", "driving", "establish",
    "ideal", "proven", "track", "record", "passionate", "motivated", "self-starter",
    "proactive", "results-driven", "detail-oriented", "fast-paced", "dynamic",
    "innovative", "collaborative", "stakeholder", "stakeholders", "cross-functional",
    "well", "within", "across", "various", "related", "also", "highly",
    "based", "plus", "like", "etc", "and/or", "need", "needs",
    "apply", "join", "offer", "opportunity", "opportunities", "have", "has", "candidates", "for", "with", "and",
}

# Set of Education Terms that MUST NOT be classified as technical skills
EDUCATION_TERMS: Set[str] = {
    "b.tech", "btech", "b.e.", "be", "m.tech", "mtech", "mca", "b.sc", "bsc",
    "m.sc", "msc", "phd", "ph.d.", "bachelor", "bachelors", "master", "masters",
    "doctorate", "degree", "diploma", "education", "university", "college", "academic"
}

# Section headers that indicate "Preferred Skills" / "Nice to Have" sections in JDs (Fix #1)
PREFERRED_SKILLS_SECTION_HEADERS: List[str] = [
    "preferred skills",
    "nice to have",
    "good to have",
    "preferred qualifications",
    "plus",
    "bonus skills",
    "desired skills",
    "additional skills",
    "nice-to-have",
    "good-to-have",
    "preferred experience",
    "preferred",
]

# Generic words that should receive LOW rarity weight in keyword relevance (Fix #5)
KEYWORD_GENERIC_WORDS: Set[str] = {
    "team", "work", "strong", "good", "excellent", "experience", "skills",
    "ability", "knowledge", "working", "required", "preferred", "minimum",
    "years", "role", "position", "candidate", "company", "job", "field",
    "industry", "relevant", "provide", "support", "develop", "design",
    "manage", "create", "ensure", "maintain", "implement", "build",
    "using", "including", "environment", "understanding", "various",
    "based", "well", "across", "within", "also", "highly", "plus",
    "like", "need", "needs", "responsible", "demonstrated", "proven",
    "detail", "oriented", "driven", "self", "fast", "paced",
    "collaborative", "innovative", "dynamic", "proactive", "motivated",
    "passionate", "deliver", "drive", "lead", "collaborate",
    "stakeholder", "stakeholders", "cross", "functional",
    "must", "will", "looking", "offers", "along", "technology",
    "hands", "ensure", "responsible", "overview", "summary",
    "description", "details", "title", "heading", "header", "profile",
}


def is_valid_skill(skill_str: str) -> bool:
    """
    Validates whether a candidate string is a genuine technical/professional skill,
    filtering out section headers, generic words, and education degree terms.
    """
    clean = skill_str.lower().strip().rstrip(":")
    if not clean or len(clean) < 2:
        return False

    if clean in GENERIC_NON_SKILL_WORDS or clean in EDUCATION_TERMS:
        return False

    # Check if phrase consists solely of generic non-skill words or education terms
    tokens = [t.strip(".:") for t in clean.split()]
    if all(t in GENERIC_NON_SKILL_WORDS or t in EDUCATION_TERMS for t in tokens):
        return False

    return True


def strip_resume_header(resume_doc: ResumeDocument) -> str:
    """
    Returns the resume body text with header/contact information stripped out.
    This prevents candidate name, email, and phone from leaking into keyword matching. (Fix #4)
    """
    if not resume_doc.sections:
        return resume_doc.raw_text

    body_parts = []
    for section in resume_doc.sections:
        # Skip the "Header" section (first section which typically has name/contact)
        norm = section.normalized_title.lower()
        if norm in ("header", "general") and section == resume_doc.sections[0]:
            continue
        body_parts.append(section.raw_text)

    body_text = "\n".join(body_parts)
    # Also explicitly strip out email and phone if they somehow leaked
    if resume_doc.contact_email:
        body_text = body_text.replace(resume_doc.contact_email, "")
    if resume_doc.contact_phone:
        body_text = body_text.replace(resume_doc.contact_phone, "")

    return body_text if body_text.strip() else resume_doc.raw_text


def compute_keyword_rarity_weights(jd_tokens: Set[str], resume_tokens: Set[str]) -> Dict[str, float]:
    """
    Computes lightweight rarity/importance weights for JD keywords. (Fix #5)
    
    Weighting strategy (pure Python, no external NLP):
    - Multi-word technical phrases: weight 3.0
    - Known technical terms (contain digits, special chars, or are short acronyms): weight 2.0
    - Generic/corporate words: weight 0.3
    - Normal words: weight 1.0
    """
    weights: Dict[str, float] = {}
    for token in jd_tokens:
        lower = token.lower()
        if lower in KEYWORD_GENERIC_WORDS:
            weights[token] = 0.3
        elif _is_technical_term(lower):
            weights[token] = 2.0
        else:
            weights[token] = 1.0
    return weights


def _is_technical_term(term: str) -> bool:
    """Heuristic to detect if a token looks like a technical term."""
    # Contains digits (e.g., python3, k8s, c++, .net)
    if any(c.isdigit() for c in term):
        return True
    # Contains special chars typical of tech terms
    if any(c in term for c in "#+."):
        return True
    # Short uppercase acronyms (2-5 chars, like SQL, AWS, GCP, API)
    if term.upper() == term and 2 <= len(term) <= 5 and term.isalpha():
        return True
    # Known technical indicators
    tech_indicators = {
        "python", "java", "javascript", "typescript", "react", "angular", "vue",
        "node", "nodejs", "docker", "kubernetes", "k8s", "aws", "azure", "gcp",
        "sql", "nosql", "mongodb", "postgresql", "postgres", "mysql", "redis",
        "git", "linux", "nginx", "apache", "jenkins", "terraform", "ansible",
        "kafka", "rabbitmq", "graphql", "rest", "api", "microservices",
        "spring", "django", "flask", "fastapi", "express", "webpack",
        "ci/cd", "devops", "agile", "scrum", "kanban", "jira",
        "html", "css", "sass", "less", "bootstrap", "tailwind",
        "elasticsearch", "kibana", "grafana", "prometheus",
        "lambda", "serverless", "containers", "containerization",
    }
    if term in tech_indicators:
        return True
    return False


def levenshtein_distance(s1: str, s2: str) -> int:
    """
    Computes Levenshtein edit distance between two strings using standard library.
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def normalized_levenshtein(s1: str, s2: str) -> float:
    """
    Calculates normalized similarity between 0.0 and 1.0 based on Levenshtein distance.
    """
    str1 = s1.lower().strip()
    str2 = s2.lower().strip()
    if str1 == str2:
        return 1.0

    max_len = max(len(str1), len(str2))
    if max_len == 0:
        return 1.0

    dist = levenshtein_distance(str1, str2)
    return max(0.0, 1.0 - (dist / max_len))


class MatchFeatures:
    """
    Extracts requirements from Job Descriptions and compares them against Resume Documents.
    """

    @classmethod
    def match_skills(cls, jd_skills: List[str], candidate_skills: List[str], candidate_tokens: List[str]) -> List[SkillMatchItem]:
        """
        Compares JD skill requirements against candidate skills using exact, alias, and fuzzy matching.
        """
        results: List[SkillMatchItem] = []
        cand_skills_lower = [s.lower().strip() for s in candidate_skills if is_valid_skill(s)]
        cand_tokens_lower = [t.lower().strip() for t in candidate_tokens if is_valid_skill(t)]

        for req_skill in jd_skills:
            req_clean = req_skill.lower().strip()
            if not is_valid_skill(req_clean):
                continue

            # 1. Exact Match
            if req_clean in cand_skills_lower or req_clean in cand_tokens_lower:
                results.append(SkillMatchItem(
                    jd_skill=req_skill,
                    resume_skill=req_skill,
                    similarity_score=1.0,
                    match_type="Exact"
                ))
                continue

            # 2. Transparent Alias Match
            aliases = SKILL_ALIASES.get(req_clean, set())
            alias_match_found = False
            for alias in aliases:
                if alias in cand_skills_lower or alias in cand_tokens_lower:
                    results.append(SkillMatchItem(
                        jd_skill=req_skill,
                        resume_skill=alias,
                        similarity_score=1.0,
                        match_type="Alias"
                    ))
                    alias_match_found = True
                    break

            if alias_match_found:
                continue

            # 3. Fuzzy Match (Strict Threshold >= 0.82)
            best_fuzzy_score = 0.0
            best_fuzzy_term = ""

            for cand_skill in cand_skills_lower:
                sim = normalized_levenshtein(req_clean, cand_skill)
                if sim > best_fuzzy_score:
                    best_fuzzy_score = sim
                    best_fuzzy_term = cand_skill

            if best_fuzzy_score >= 0.82:
                results.append(SkillMatchItem(
                    jd_skill=req_skill,
                    resume_skill=best_fuzzy_term,
                    similarity_score=best_fuzzy_score,
                    match_type="Fuzzy"
                ))
            else:
                results.append(SkillMatchItem(
                    jd_skill=req_skill,
                    resume_skill="",
                    similarity_score=0.0,
                    match_type="Missing"
                ))

        return results

    @classmethod
    def parse_experience_years(cls, text: str) -> Optional[float]:
        """
        Parses required or stated experience years from text (e.g. '3+ years', 'minimum 5 years').
        """
        if not text:
            return None

        # Pattern: "3+ years", "3-5 years", "minimum 3 years", "3 yrs"
        pattern = re.compile(r'(?:minimum\s+)?(\d+)(?:\+|\s*-\s*\d+)?\s*(?:years?|yrs?)', re.IGNORECASE)
        matches = pattern.findall(text)
        if matches:
            try:
                nums = [float(m) for m in matches]
                return max(nums)
            except ValueError:
                pass
        return None

    @classmethod
    def parse_education_degrees(cls, text: str) -> List[str]:
        """
        Extracts recognized degree types from text.
        """
        if not text:
            return []

        found_degrees = []
        lower_text = text.lower()

        for canonical, aliases in EDUCATION_DEGREES.items():
            for alias in aliases:
                if re.search(r'\b' + re.escape(alias) + r'\b', lower_text):
                    found_degrees.append(canonical)
                    break

        return found_degrees

    @classmethod
    def parse_certifications(cls, text: str) -> List[str]:
        """
        Extracts certifications from text.
        """
        if not text:
            return []

        certs = ["aws", "pmp", "cism", "cissp", "scrum master", "certified", "azure", "gcp", "ckad", "cka"]
        found = []
        lower_text = text.lower()
        for cert in certs:
            if re.search(r'\b' + re.escape(cert) + r'\b', lower_text):
                found.append(cert.upper() if len(cert) <= 4 else cert.title())

        return found

    @classmethod
    def extract_skills_from_text(cls, text: str) -> List[str]:
        """
        Extracts valid technical/professional skill items from text blocks,
        filtering out section headers, generic words, and education degrees.
        """
        if not text:
            return []

        lines = text.split('\n')
        skills = []

        for line in lines:
            stripped = line.strip()
            # Ignore lines that are section headers ending with a colon
            if stripped.endswith(":") and len(stripped.split()) <= 4:
                continue

            # Split line by comma, semicolon, bullet symbols, tabs
            items = re.split(r'[,;•\*\-\t]', stripped)
            for item in items:
                cleaned_item = item.strip().rstrip(":")
                if not cleaned_item:
                    continue
                if is_valid_skill(cleaned_item):
                    skills.append(cleaned_item)
                else:
                    # Tokenize the item into individual words to check them independently.
                    # This ensures we extract "Python" from "must have Python" and discard filler words.
                    words = re.findall(r'[a-zA-Z0-9_\+\#\.\-]+', cleaned_item)
                    for word in words:
                        cleaned_word = word.strip().rstrip(":")
                        if is_valid_skill(cleaned_word):
                            skills.append(cleaned_word)

        # De-duplicate while preserving order
        seen = set()
        unique_skills = []
        for s in skills:
            s_lower = s.lower().strip()
            if s_lower not in seen:
                seen.add(s_lower)
                unique_skills.append(s)

        return unique_skills

    @classmethod
    def extract_preferred_skills_from_jd(cls, jd_doc: JobDescription) -> List[str]:
        """
        Extracts preferred/nice-to-have skills from JD by looking for
        known preferred-skills section headers. (Fix #1)

        Returns an empty list if no such section exists.
        """
        preferred_skills: List[str] = []

        # Strategy 1: Look for a matching section by normalized title
        for section in jd_doc.sections:
            section_name_lower = section.name.lower().strip().rstrip(":")
            norm_title_lower = section.normalized_title.lower().strip()

            for header in PREFERRED_SKILLS_SECTION_HEADERS:
                if header in section_name_lower or header in norm_title_lower:
                    skills = cls.extract_skills_from_text(section.raw_text)
                    preferred_skills.extend(skills)
                    break

        # Strategy 2: Regex scan for inline "Nice to Have:" / "Preferred Skills:" blocks
        if not preferred_skills:
            pattern = re.compile(
                r'(?:preferred\s+skills?|nice\s+to\s+have|good\s+to\s+have|'
                r'preferred\s+qualifications?|bonus\s+skills?|desired\s+skills?)\s*[:\-]\s*'
                r'([^\n]+(?:\n(?!\n)[^\n]+)*)',
                re.IGNORECASE
            )
            for match in pattern.finditer(jd_doc.raw_text):
                block = match.group(1)
                skills = cls.extract_skills_from_text(block)
                preferred_skills.extend(skills)

        # De-duplicate while preserving order
        seen: Set[str] = set()
        unique: List[str] = []
        for s in preferred_skills:
            key = s.lower().strip()
            if key not in seen:
                seen.add(key)
                unique.append(s)

        return unique

# Master Specification: Zero-Dependency Resume Intelligence Platform

## Project Overview
The Zero-Dependency Resume Intelligence Platform is a local, explainable resume analysis engine written entirely using the standard programming language features (Python 3 standard library). It provides two distinct, uncoupled capabilities:
1. **Resume AI-Generated Likelihood Detection**
2. **Resume-to-Job Description (JD) Matching**

## Strict Constraints & Principles
1. **Zero External Dependencies**: NO external packages (e.g. nltk, spacy, scikit-learn, numpy, pdfplumber, torch), libraries, third-party APIs, or pre-trained AI models are allowed for resume analysis and scoring logic. Only Python built-in modules (`re`, `math`, `collections`, `json`, `dataclasses`, `pathlib`, `typing`, `argparse`, `html`, `http.server`, `unittest`, etc.) may be used.
2. **Separation of Concerns**: Resume AI-generated likelihood detection and Resume-JD matching MUST be implemented in completely separate, decoupled modules with independent scoring models.
3. **100% Explainable Scoring**: Every score (0-100%) must be accompanied by detailed metrics, token breakdowns, weightings, flagged phrases, matched/missing skills, and natural language explanations.
4. **No Feature Creep**: Only implement features specified in this master document.

---

## Module Specifications

### Module 1: Core Text Processing & Ingestion (`src/core/`)
- **Document Structure**: Data models for `ResumeDocument`, `JobDescription`, and `Section`.
- **Text Preprocessing**: Lowercasing, tokenization, custom English stopword removal, sentence splitting, stemming/lemmatization approximations (rule-based suffix stripping).
- **Section Parsing**: Rule-based section detection (Header/Contact, Executive Summary, Work Experience, Education, Skills, Projects, Certifications).

### Module 2: Resume AI Likelihood Detector (`src/ai_detection/`)
- **Statistical & Stylometric Indicators**:
  1. **Vocabulary Over-representation / AI Cliché Index**: Frequency analysis of overused LLM words ("delve", "spearheaded", "realm", "synergy", "testament", "dynamic", "pivotal", "transformative", "beacon", "mastery", "tapestry", "seamless", "cutting-edge").
  2. **Sentence Length Burstiness**: Standard deviation and coefficient of variation of sentence lengths (word counts). AI text tends to have uniform sentence lengths (low burstiness).
  3. **Syntactic Uniformity & Repetitive Starters**: Detection of repeated sentence-starting POS patterns / transition words ("Additionally,", "Furthermore,", "Moreover,", "In addition,").
  4. **Perplexity Proxy (N-Gram Predictability)**: Measure of vocabulary entropy and repetitive bi-gram / tri-gram usage compared to natural resume text baselines.
- **Explainability**: Output a 0-100% AI Likelihood Score with sub-score breakdowns, list of flagged phrases with line numbers, and a burstiness score explanation.

### Module 3: Resume-to-JD Matcher (`src/jd_matching/`)
- **Matching Algorithms**:
  1. **Keyword Overlap & TF-IDF Scoring**: Term frequency calculation weighted by inverse document frequency across JD key terms.
  2. **Skill Extraction & Fuzzy Matching**: Custom Levenshtein distance and Jaccard similarity for skill variations (e.g., "ReactJS" vs "React.js", "Python 3" vs "Python").
  3. **Experience & Role Alignment**: Section-specific matching for work experience duration, job titles, and responsibilities.
- **Explainability**: Output an overall Match Score (0-100%), weighted section scores (Hard Skills 40%, Experience 30%, Education 10%, Soft Skills/Keywords 20%), detailed list of Matched Skills, Missing Skills, and tailored resume optimization recommendations.

### Module 4: Unified Reporter & CLI/Web Engine (`src/reporter/` & `app.py`)
- **CLI Interface**: Command-line interface to analyze single resumes or batches against JDs.
- **HTML/JSON Report Generator**: Generate stand-alone visual HTML reports with interactive breakdown charts and structured JSON outputs.

---

## Implementation Roadmap (Stages)

### Stage 1: Core Text Ingestion & Parsing Engine (CURRENT STAGE)
- Implement `src/core/models.py` (`ResumeDocument`, `JobDescription`, `ParsedSection`).
- Implement `src/core/text_processing.py` (tokenization, sentence segmentation, stopword filtering, n-gram generation, rule-based suffix stemming).
- Implement `src/core/section_parser.py` (extracting sections, key contact information, bullet points, and section categorization).
- Implement unit tests in `tests/test_core.py` verifying parsing, tokenization, and section extraction.

### Stage 2: Resume AI Likelihood Detection Module
- Implement `src/ai_detection/cliche_dictionary.py` and `src/ai_detection/burstiness.py`.
- Implement `src/ai_detection/detector.py` (combining cliche score, burstiness score, transition score, and n-gram predictability).
- Implement unit tests in `tests/test_ai_detection.py`.

### Stage 3: Resume-to-JD Matching Engine
- Implement `src/jd_matching/fuzzy.py` (Levenshtein distance, Jaccard similarity).
- Implement `src/jd_matching/skills_extractor.py` and `src/jd_matching/matcher.py`.
- Implement unit tests in `tests/test_jd_matching.py`.

### Stage 4: Orchestration, Reporting & CLI Interface
- Implement `src/reporter/formatter.py` (JSON and HTML report creation).
- Implement main CLI script `app.py` for command-line execution and batch processing.
- End-to-end integration tests in `tests/test_integration.py`.
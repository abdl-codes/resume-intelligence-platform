# Zero-Dependency Resume Intelligence Platform

A local, explainable resume analysis engine written entirely using the Python 3 standard library. The platform runs a local HTTP server providing a recruiter dashboard and API endpoints for resume evaluation against job descriptions.

## Purpose
This platform enables recruiters to parse resumes, compute match scores relative to job descriptions (JD), and evaluate the likelihood that a resume was generated using AI tools. It achieves this with zero external package dependencies.

## Features
1. **Resume-to-JD Matching**:
   - Compares candidate resumes against job descriptions.
   - Dynamic weight normalization handles omitted JD requirements gracefully.
   - Computes match scores across multiple categories: required/preferred skills, work experience duration, degree alignment, certifications, responsibilities, and keyword relevance.
2. **AI-Generated Likelihood Detection**:
   - Independently calculates the probability that a resume was AI-written using stylometric and statistical indices.
   - Evaluates phrase clichés, sentence length burstiness, transition frequency, n-gram predictability, lexical diversity, repetition, and structural consistency.
3. **100% Explainable Scoring**:
   - All scores are accompanied by explanations detailing matched skills, missing skills, flagged cliché words, and improvement recommendations.
4. **Recruiter Dashboard**:
   - A lightweight vanilla HTML/CSS/JS frontend to upload multiple resumes, input JDs, and visualize the analysis results.

## Technology Stack
- **Backend**: Python 3 (Pure standard library: `http.server`, `json`, `cgi`, `re`, `math`, `collections`, `dataclasses`, `pathlib`, `urllib`, `argparse`).
- **Frontend**: Vanilla HTML5, Vanilla CSS3 (custom glassmorphism dark theme), and Vanilla JavaScript.
- **Dependencies**: None.

## Project Structure
```
coe/
├── app.py                     # Main application entry point (CLI/server start)
├── smoke_test.py              # Script to perform a quick integration test of the API
├── notes.md                   # Project design specification notes
├── README.md                  # Project setup and usage documentation
├── HANDOFF.md                 # System handoff documentation for developers/AI agents
├── src/
│   ├── __init__.py
│   ├── core/                  # Core text processing, parsing, and data models
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── section_parser.py
│   │   └── text_processing.py
│   ├── ai_detection/          # AI generation likelihood detector and scoring
│   │   ├── __init__.py
│   │   ├── detector.py
│   │   ├── features.py
│   │   ├── models.py
│   │   └── scoring.py
│   ├── jd_matching/           # Resume ↔ JD matching algorithm and scoring
│   │   ├── __init__.py
│   │   ├── features.py
│   │   ├── matcher.py
│   │   ├── models.py
│   │   └── scoring.py
│   └── app/                   # HTTP Server and orchestration layers
│       ├── __init__.py
│       ├── orchestrator.py
│       ├── server.py
│       └── static/            # Static assets for recruiter dashboard web frontend
│           ├── app.js
│           ├── index.html
│           └── styles.css
└── tests/                     # Unit and integration test suites
    ├── __init__.py
    ├── test_ai_detection.py
    ├── test_core.py
    ├── test_integration.py
    ├── test_jd_matching.py
    └── test_scoring_improvements.py
```

## Installation & Setup
No external package installation is required. Ensure you have Python 3.12+ installed.

### Setup environment variables:
Create a `.env` file in the root directory to store configuration values. Example:
```ini
PORT=8081
HOST=127.0.0.1
```

## Running the Application
Start the server locally on port 8081:
```bash
python app.py --port 8081
```

Or run via the specific python installation:
```bash
& "C:\Users\lenovo\AppData\Local\Programs\Python\Python312\python.exe" app.py --port 8081
```

Once running, you can access the dashboard at:
[http://localhost:8081](http://localhost:8081)

## Running Tests
Run all unit and integration tests using standard unittest discovery:
```bash
python -m unittest discover -s tests
```

## Core Scoring Formulas

### 1. Job Description Matching Score
The matching engine uses dynamic weight redistribution so that missing JD requirements (e.g., no certifications required) do not artificially penalize candidates.
- **Weights**: Required Skills (40%), Preferred Skills (10%), Experience (15%), Education (10%), Certifications (5%), Responsibilities (10%), Keyword Relevance (10%).
- **Calculation**:
  $$\text{Final Score} = \frac{\sum (\text{Active Component Score} \times \text{Active Weight})}{\sum \text{Active Weights}} \times 100$$
- If a component is marked inactive (e.g. no preferred skills in the JD), its weight is excluded and the denominator is adjusted.

### 2. AI Likelihood Score
The AI detector uses stylometrics to find robotic text formatting:
- **Weights**: Cliche Density (30%), Sentence Burstiness (20%), Transition Density (20%), N-gram Predictability (15%), Lexical Diversity (5%), Repetition Index (5%), Structural Consistency (5%).
- **Calculation**: Sum of each active stylometric check's weighted normalized score.

## Important Implementation Details
- **Zero Dependencies**: You must not introduce `pip install` packages into `src/`.
- **Explainability**: Both scoring engines are structured around generating explicit component breakdowns with natural language explanations returned in the JSON API.

## Known Limitations
- Text parsing is rule-based and optimized for `.txt` resumes. PDF or Word documents must be converted to plain text before ingestion.
- Multi-word skill extraction uses word-splitting heuristics and fallback token check procedures.

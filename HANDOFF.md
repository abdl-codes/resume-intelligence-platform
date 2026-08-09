# Project Handoff Documentation

This document summarizes the current status of the project, details completed work, and provides guidance for the next coding agent.

## Current Project Status
- The local server starts and listens on port `8081`.
- The frontend dashboard loads and functions as expected.
- Programmatic testing verifies that the API receives multiple resumes and processes JD-to-resume analysis correctly.
- Test suites run using `unittest`, with 99 out of 100 passing. One unit test (`test_filler_words_not_extracted_from_jd` in `tests/test_scoring_improvements.py`) is currently failing due to a minor skill parsing boundary issue.

## Completed Tasks
- **Server Verification**: Verified that the server starts on port `8081` without duplicates.
- **API and Upload Testing**: Successfully tested uploading multiple resumes (`alice_johnson.txt`, `bob_smith.txt`, `carol_williams.txt`) against a sample Python Developer job description. Verified response structures and ranking logic.
- **Git & Environment Security**: Ensured that the `.env` file containing variables remains untracked and is correctly ignored via `.gitignore`.
- **Cleanup**: Cleaned up the `backups/` directory containing temporary development artifacts.

## Scoring Algorithms

### Job Description Matching
- **Component Weights**: Required Skills (40%), Preferred Skills (10%), Experience (15%), Education (10%), Certifications (5%), Responsibilities (10%), Keyword Relevance (10%).
- **Dynamic Weight Redistribution**: Excludes inactive components if the Job Description does not specify requirements for that category.
- **Calculations**: Sums the active component scores multiplied by their weights, divided by the sum of active weights.

### AI Generated Text Likelihood
- **Component Weights**: Cliche Density (30%), Sentence Burstiness (20%), Transition Density (20%), N-gram Predictability (15%), Lexical Diversity (5%), Repetition Index (5%), Structural Consistency (5%).

## Important Files
- [app.py](file:///c:/Users/lenovo/OneDrive/Documents/coe/app.py): Entry point to start the local server.
- [src/app/server.py](file:///c:/Users/lenovo/OneDrive/Documents/coe/src/app/server.py): Base HTTP Server handling JSON and multipart form data.
- [src/jd_matching/scoring.py](file:///c:/Users/lenovo/OneDrive/Documents/coe/src/jd_matching/scoring.py): Matches resumes to JDs and redistributes weights.
- [src/ai_detection/scoring.py](file:///c:/Users/lenovo/OneDrive/Documents/coe/src/ai_detection/scoring.py): Scores stylometric features to compute AI probability.
- [src/jd_matching/features.py](file:///c:/Users/lenovo/OneDrive/Documents/coe/src/jd_matching/features.py): Feature extraction and skill extraction methods.
- [smoke_test.py](file:///c:/Users/lenovo/OneDrive/Documents/coe/smoke_test.py): Integration helper sending multiple resumes via multipart request.

## Commands to Run the Application
Start the server:
```bash
& "C:\Users\lenovo\AppData\Local\Programs\Python\Python312\python.exe" app.py --port 8081
```

Run test suite:
```bash
& "C:\Users\lenovo\AppData\Local\Programs\Python\Python312\python.exe" -m unittest discover -s tests
```

## Instructions for the Next Agent
1. **Fix Failing Unit Test**:
   - Locate `test_filler_words_not_extracted_from_jd` inside `tests/test_scoring_improvements.py`.
   - Modify the skill splitting/extraction logic in `extract_skills_from_text` (inside `src/jd_matching/features.py`) to split complex candidate phrases (like `"must have strong Python experience"`) into individual token checks when they fail initial validation, ensuring terms like `"Python"` are properly isolated.
2. **Scoring Logic**:
   - Retain the pure Python standard library structure; do not add external third-party library dependencies.
   - Maintain the dynamic weight adjustment engine currently implemented in `src/jd_matching/scoring.py`.

"""
Lightweight HTTP Server and API for the Resume Intelligence Platform.
Uses only Python standard library: http.server, json, cgi, pathlib.
No Flask, Django, FastAPI, or any external packages.
"""
import json
import os
import sys
import cgi
import io
import mimetypes
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Dict, Any, Optional
from urllib.parse import unquote

from src.app.orchestrator import run_full_analysis

# Directory containing static frontend assets (index.html, styles.css, app.js)
STATIC_DIR = Path(__file__).parent / "static"

# Supported resume file extensions (text-based)
SUPPORTED_EXTENSIONS = {".txt", ".text", ".md", ".csv", ".log"}
MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10 MB limit


def _read_text_file_safely(raw_bytes: bytes, filename: str) -> str:
    """Attempts to decode uploaded file bytes to text with multiple fallback encodings."""
    for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252", "ascii"):
        try:
            return raw_bytes.decode(encoding)
        except (UnicodeDecodeError, ValueError):
            continue
    return ""


class ResumeAPIHandler(BaseHTTPRequestHandler):
    """
    HTTP Request Handler for the Resume Intelligence Platform.

    Routes:
        GET  /             → serves index.html
        GET  /static/<f>   → serves static assets
        POST /api/analyze  → runs the analysis pipeline
    """

    # Suppress default stderr logging of every request
    def log_message(self, format, *args):
        pass  # silence per-request logs in production; remove for debugging

    def _send_json(self, data: Dict[str, Any], status: int = 200) -> None:
        """Helper to send a JSON response."""
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, filepath: Path) -> None:
        """Serves a static file with appropriate MIME type."""
        if not filepath.exists() or not filepath.is_file():
            self._send_json({"error": "File not found"}, 404)
            return

        # Security: ensure the resolved path is inside STATIC_DIR
        try:
            filepath.resolve().relative_to(STATIC_DIR.resolve())
        except ValueError:
            self._send_json({"error": "Forbidden"}, 403)
            return

        content_type, _ = mimetypes.guess_type(str(filepath))
        if content_type is None:
            content_type = "application/octet-stream"

        content = filepath.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(content)

    # ------------------------------------------------------------------
    # GET Handler
    # ------------------------------------------------------------------
    def do_GET(self) -> None:
        path = unquote(self.path).split("?")[0]  # strip query string

        if path == "/" or path == "/index.html":
            self._send_file(STATIC_DIR / "index.html")

        elif path.startswith("/static/"):
            rel = path[len("/static/"):]
            self._send_file(STATIC_DIR / rel)

        else:
            self._send_json({"error": "Not found"}, 404)

    # ------------------------------------------------------------------
    # POST Handler
    # ------------------------------------------------------------------
    def do_POST(self) -> None:
        path = unquote(self.path).split("?")[0]

        if path != "/api/analyze":
            self._send_json({"error": "Not found"}, 404)
            return

        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length > MAX_REQUEST_SIZE:
                self._send_json({"status": "error", "error": "Request body too large (exceeds 10MB limit)."}, 413)
                return

            content_type_header = self.headers.get("Content-Type", "")

            if "multipart/form-data" in content_type_header:
                self._handle_multipart()
            elif "application/json" in content_type_header:
                self._handle_json_post()
            else:
                self._send_json(
                    {"status": "error", "error": "Unsupported Content-Type. Use multipart/form-data or application/json."},
                    400
                )

        except Exception as exc:
            self._send_json(
                {"status": "error", "error": f"Server error: {str(exc)}"},
                500
            )

    def _handle_multipart(self) -> None:
        """Parses multipart/form-data containing JD text and resume files."""
        content_type_header = self.headers.get("Content-Type", "")
        content_length = int(self.headers.get("Content-Length", 0))

        # Read body
        body = self.rfile.read(content_length)

        # Parse using cgi.parse_multipart-compatible approach
        # We need to use the email/cgi module to parse multipart
        environ = {
            "REQUEST_METHOD": "POST",
            "CONTENT_TYPE": content_type_header,
            "CONTENT_LENGTH": str(content_length),
        }

        fs = cgi.FieldStorage(
            fp=io.BytesIO(body),
            environ=environ,
            keep_blank_values=True,
        )

        # Extract JD text
        jd_text = ""
        jd_field = fs.getvalue("jd_text", "")
        if isinstance(jd_field, bytes):
            jd_text = jd_field.decode("utf-8", errors="replace")
        elif isinstance(jd_field, str):
            jd_text = jd_field

        # If JD text is empty, check for a JD file upload
        if not jd_text.strip():
            jd_file = fs.getvalue("jd_file", None)
            if jd_file:
                if isinstance(jd_file, bytes):
                    jd_text = jd_file.decode("utf-8", errors="replace")
                elif isinstance(jd_file, str):
                    jd_text = jd_file

        # Extract resume files
        resumes = []
        
        if "resumes" in fs:
            resume_fields = fs["resumes"]
        elif "resume" in fs:
            resume_fields = fs["resume"]
        else:
            resume_fields = []
            
        if not isinstance(resume_fields, list):
            resume_fields = [resume_fields]

        for item in resume_fields:
            if hasattr(item, "filename") and item.filename:
                # Sanitize filename (prevent path traversal / XSS)
                filename = os.path.basename(item.filename.replace("\\", "/"))
                raw = item.file.read() if hasattr(item, "file") else (item.value if isinstance(item.value, bytes) else item.value.encode("utf-8"))
            elif hasattr(item, "value"):
                filename = getattr(item, "filename", None) or "uploaded.txt"
                raw = item.value if isinstance(item.value, bytes) else item.value.encode("utf-8")
            else:
                continue

            # Check extension
            ext = os.path.splitext(filename)[1].lower()
            if ext and ext not in SUPPORTED_EXTENSIONS:
                resumes.append((filename, ""))  # will produce validation error
                continue

            text = _read_text_file_safely(raw, filename)
            resumes.append((filename, text))

        # Run the analysis pipeline
        result = run_full_analysis(jd_text, resumes)
        status_code = 200 if result.get("status") == "success" else 400
        self._send_json(result, status_code)

    def _handle_json_post(self) -> None:
        """Handles application/json POST for programmatic API access."""
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length)

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            self._send_json({"status": "error", "error": f"Invalid JSON: {str(exc)}"}, 400)
            return

        jd_text = payload.get("jd_text", "")
        resumes_data = payload.get("resumes", [])

        resumes = []
        for item in resumes_data:
            if isinstance(item, dict):
                resumes.append((item.get("filename", "resume.txt"), item.get("text", "")))
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                resumes.append((str(item[0]), str(item[1])))

        result = run_full_analysis(jd_text, resumes)
        status_code = 200 if result.get("status") == "success" else 400
        self._send_json(result, status_code)


def start_server(host: str = "127.0.0.1", port: int = 8080) -> None:
    """Starts the Resume Intelligence Platform HTTP server."""
    server = HTTPServer((host, port), ResumeAPIHandler)
    print(f"\n{'=' * 60}")
    print(f"  Resume Intelligence Platform")
    print(f"  Explainable Resume Verification & Job Matching")
    print(f"{'=' * 60}")
    print(f"  Server running at:  http://{host}:{port}")
    print(f"  Press Ctrl+C to stop")
    print(f"{'=' * 60}\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.server_close()

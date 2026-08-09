"""
Resume Intelligence Platform — Application Entry Point
Starts the local HTTP server for the recruiter dashboard.

Usage:
    python app.py                  # starts at http://127.0.0.1:8080
    python app.py --port 9000      # custom port
    python app.py --host 0.0.0.0   # bind to all interfaces

Pure Python Standard Library. No external packages.
"""
import argparse
import sys
import os

# Ensure the project root is on sys.path so `src.*` imports resolve correctly
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Load environment variables from .env file to secure API keys
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
except ImportError:
    # Minimal fallback parser if python-dotenv is not installed
    env_path = os.path.join(PROJECT_ROOT, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

# Example of accessing the secure environment variable
# API_KEY = os.environ.get("OPENAI_API_KEY", "")

from src.app.server import start_server


def main():
    parser = argparse.ArgumentParser(
        description="Resume Intelligence Platform — Local Recruiter Dashboard"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host address to bind to (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port number to listen on (default: 8080)"
    )
    args = parser.parse_args()

    start_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()

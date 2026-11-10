"""
run.py — Launch the IBM Research Agent web application.

Usage
-----
    python run.py
    python run.py --port 8080
    python run.py --host 0.0.0.0 --port 5000 --debug
"""

import argparse
import sys
import os

# Ensure project root is on path regardless of working directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    parser = argparse.ArgumentParser(description="IBM Research Agent Web App")
    parser.add_argument("--host",  default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    parser.add_argument("--port",  default=5000, type=int, help="Port to listen on (default: 5000)")
    parser.add_argument("--debug", action="store_true", help="Enable Flask debug mode")
    args = parser.parse_args()

    # Validate IBM credentials before starting the server
    try:
        from research_agent import config  # noqa: F401 — triggers env validation
    except EnvironmentError as exc:
        print(f"\n❌  Configuration Error: {exc}")
        print("\nTip: Copy env.example → .env.local and fill in your IBM Cloud credentials.\n")
        sys.exit(1)

    from webapp.app import app

    print(f"\n🔬  IBM Research Agent")
    print(f"    Powered by IBM Llama-3 on IBM Cloud Lite")
    print(f"    Running at: http://{args.host}:{args.port}\n")

    app.run(
        host=args.host,
        port=args.port,
        debug=args.debug,
        threaded=True,
    )


if __name__ == "__main__":
    main()

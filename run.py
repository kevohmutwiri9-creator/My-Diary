#!/usr/bin/env python3
"""Simple development server for My Diary application."""

import os

from app import create_app

app = create_app()


def _resolve_port(default: int = 5000) -> int:
    """Return the port configured via environment variable (Render uses $PORT)."""
    try:
        return int(os.environ.get("PORT", default))
    except ValueError:
        return default


if __name__ == '__main__':
    port = _resolve_port()
    print("🚀 Starting My Diary...")
    print(f"📖 Open http://localhost:{port} in your browser")
    print("Press Ctrl+C to stop")
    app.run(debug=True, host='0.0.0.0', port=port)

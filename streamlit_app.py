"""Hugging Face Spaces entry point (Spaces auto-detect streamlit_app.py)."""
from __future__ import annotations

import sys
from pathlib import Path

_PKG_DIR = Path(__file__).resolve().parent / "modern_dashboard"
if str(_PKG_DIR) not in sys.path:
    sys.path.insert(0, str(_PKG_DIR))

import app  # noqa: E402,F401  (runs the app on import)

"""Deployment entry point. Runs the Streamlit app from the repo root.

Deployment platforms (Streamlit Cloud, Hugging Face Spaces, Render) run the
app from the repo root. modern_dashboard/app.py imports its siblings
(data_loader, analytics, ...) as top-level modules, so we prepend the
modern_dashboard package dir to sys.path before importing.
"""
from __future__ import annotations

import sys
from pathlib import Path

_PKG_DIR = Path(__file__).resolve().parent / "modern_dashboard"
if str(_PKG_DIR) not in sys.path:
    sys.path.insert(0, str(_PKG_DIR))

# NOTE: app.py itself is not part of the modern_dashboard package (it has no
# package-relative imports), so importing it as a top-level module is correct.
import app  # noqa: E402,F401  (runs the app on import)

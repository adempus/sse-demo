"""Pytest configuration — isolate the database to a temp file per session."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

# Point the app at a throwaway SQLite file before app modules import.
_tmp = Path(tempfile.gettempdir()) / "sse_state_demo_test.db"
_tmp.unlink(missing_ok=True)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp}"

"""
File Manager Utility
─────────────────────────────────────────────
Manages session directories for uploaded videos and extracted frames.
Handles creation, cleanup, and path resolution.
"""

import shutil
import time
from pathlib import Path
from typing import Optional


SESSIONS_DIR = Path("sessions")
STATIC_THUMBNAILS = Path("static/thumbnails")


class FileManager:

    def __init__(self):
        SESSIONS_DIR.mkdir(exist_ok=True)
        STATIC_THUMBNAILS.mkdir(parents=True, exist_ok=True)

    def create_session(self, session_id: str) -> Path:
        """Create a directory for a new analysis session."""
        session_dir = SESSIONS_DIR / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir

    def get_session(self, session_id: str) -> Optional[Path]:
        """Get session directory path if it exists."""
        session_dir = SESSIONS_DIR / session_id
        return session_dir if session_dir.exists() else None

    def cleanup_session(self, session_id: str, keep_thumbnail: bool = True):
        """
        Remove the session directory to free disk space.
        Thumbnail is already copied to static/thumbnails if keep_thumbnail=True.
        """
        session_dir = SESSIONS_DIR / session_id
        if session_dir.exists():
            try:
                shutil.rmtree(session_dir)
            except Exception:
                pass  # Best effort cleanup

    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """Remove sessions older than max_age_hours."""
        cutoff = time.time() - (max_age_hours * 3600)
        for session_dir in SESSIONS_DIR.iterdir():
            if session_dir.is_dir():
                mtime = session_dir.stat().st_mtime
                if mtime < cutoff:
                    shutil.rmtree(session_dir, ignore_errors=True)

    def cleanup_old_thumbnails(self, max_age_hours: int = 48):
        """Remove thumbnails older than max_age_hours."""
        cutoff = time.time() - (max_age_hours * 3600)
        for thumb in STATIC_THUMBNAILS.glob("*.jpg"):
            if thumb.stat().st_mtime < cutoff:
                thumb.unlink(missing_ok=True)

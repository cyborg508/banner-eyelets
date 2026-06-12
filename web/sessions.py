from __future__ import annotations

import os
import time
import uuid
from pathlib import Path
from typing import Dict, Optional

import fitz

from banner_eyelets.geometry import pt_to_cm

SESSIONS_DIR = Path(os.environ.get("BANNER_SESSIONS_DIR", "/tmp/banner-eyelets-web"))


class SessionStore:
    def __init__(self) -> None:
        self._sessions: Dict[str, dict] = {}
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    def create(self, pdf_data: bytes) -> tuple[str, float, float, int]:
        """Store PDF bytes, return (sid, width_cm, height_cm, page_count)."""
        sid = str(uuid.uuid4())
        path = SESSIONS_DIR / f"{sid}.pdf"
        path.write_bytes(pdf_data)
        doc = fitz.open(str(path))
        rect = doc[0].rect
        page_count = doc.page_count
        doc.close()
        width_cm = pt_to_cm(rect.width)
        height_cm = pt_to_cm(rect.height)
        self._sessions[sid] = {
            "path": path,
            "created": time.time(),
            "width_cm": width_cm,
            "height_cm": height_cm,
            "page_count": page_count,
        }
        return sid, width_cm, height_cm, page_count

    def get(self, sid: str) -> Optional[dict]:
        return self._sessions.get(sid)

    def sweep(self, max_age_hours: float = 2.0) -> None:
        cutoff = time.time() - max_age_hours * 3600
        stale = [s for s, e in self._sessions.items() if e["created"] < cutoff]
        for sid in stale:
            entry = self._sessions.pop(sid)
            try:
                entry["path"].unlink(missing_ok=True)
            except Exception:
                pass

import os
import time
import pytest
import fitz
from pathlib import Path
from web.sessions import SessionStore


@pytest.fixture
def store(tmp_path):
    os.environ["BANNER_SESSIONS_DIR"] = str(tmp_path / "sessions")
    import importlib
    import web.sessions
    importlib.reload(web.sessions)
    from web.sessions import SessionStore
    return SessionStore()


def test_create_stores_pdf(store, sample_pdf_bytes):
    sid, w, h, pages = store.create(sample_pdf_bytes)
    assert isinstance(sid, str) and len(sid) == 36  # UUID4
    assert abs(w - 21.0) < 0.1
    assert abs(h - 29.7) < 0.1
    assert pages == 1


def test_get_returns_entry(store, sample_pdf_bytes):
    sid, _, _, _ = store.create(sample_pdf_bytes)
    entry = store.get(sid)
    assert entry is not None
    assert entry["path"].exists()
    assert abs(entry["width_cm"] - 21.0) < 0.1


def test_get_unknown_returns_none(store):
    assert store.get("nonexistent-sid") is None


def test_sweep_removes_old(store, sample_pdf_bytes):
    sid, _, _, _ = store.create(sample_pdf_bytes)
    # backdate creation
    store._sessions[sid]["created"] = time.time() - 7201
    store.sweep(max_age_hours=2.0)
    assert store.get(sid) is None


def test_sweep_keeps_fresh(store, sample_pdf_bytes):
    sid, _, _, _ = store.create(sample_pdf_bytes)
    store.sweep(max_age_hours=2.0)
    assert store.get(sid) is not None

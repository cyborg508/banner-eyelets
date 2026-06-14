import os
import pytest
from fastapi.testclient import TestClient
from web.sessions import SessionStore
from web.server import create_app


@pytest.fixture
def client(tmp_path, sample_pdf_bytes):
    os.environ["BANNER_SESSIONS_DIR"] = str(tmp_path / "sessions")
    import importlib, web.sessions
    importlib.reload(web.sessions)
    from web.sessions import SessionStore
    app = create_app(SessionStore())
    return TestClient(app, raise_server_exceptions=True)


def test_upload_returns_dims(client, sample_pdf_bytes):
    r = client.post("/api/upload", files={"file": ("test.pdf", sample_pdf_bytes, "application/pdf")})
    assert r.status_code == 200
    data = r.json()
    assert abs(data["width_cm"] - 21.0) < 0.1
    assert abs(data["height_cm"] - 29.7) < 0.1
    assert "sid" in data
    assert data["page_count"] == 1


def test_upload_sets_cookie(client, sample_pdf_bytes):
    r = client.post("/api/upload", files={"file": ("test.pdf", sample_pdf_bytes, "application/pdf")})
    assert r.status_code == 200
    assert "sid" in r.cookies


def test_upload_rejects_non_pdf(client):
    r = client.post("/api/upload", files={"file": ("bad.txt", b"not a pdf", "text/plain")})
    assert r.status_code == 400


def test_preview_returns_png(client, sample_pdf_bytes):
    client.post("/api/upload", files={"file": ("test.pdf", sample_pdf_bytes, "application/pdf")})
    r = client.get("/api/preview?out_w=21&out_h=29.7&margin=1.5&spacing=50&marker=1")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert r.content[:4] == b"\x89PNG"


def test_preview_no_session(client):
    from fastapi.testclient import TestClient
    from web.sessions import SessionStore
    import os
    os.environ["BANNER_SESSIONS_DIR"] = "/tmp/banner-eyelets-nosession"
    fresh_app = create_app(SessionStore())
    fresh_client = TestClient(fresh_app, raise_server_exceptions=False)
    r = fresh_client.get("/api/preview?out_w=21&out_h=29.7")
    assert r.status_code == 401


def test_generate_returns_pdf(client, sample_pdf_bytes):
    client.post("/api/upload", files={"file": ("test.pdf", sample_pdf_bytes, "application/pdf")})
    r = client.get("/api/generate?out_w=21&out_h=29.7&margin=1.5&spacing=50&marker=1")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert "attachment" in r.headers["content-disposition"]
    assert r.content[:4] == b"%PDF"


def test_preview_accepts_new_params(client, sample_pdf_bytes):
    client.post("/api/upload", files={"file": ("test.pdf", sample_pdf_bytes, "application/pdf")})
    r = client.get(
        "/api/preview?out_w=21&out_h=29.7&margin=1.5&spacing=50&marker=1"
        "&border=true&frame_mm=1&frame_color=c&cross_mm=1.2"
    )
    assert r.status_code == 200
    assert r.content[:4] == b"\x89PNG"


def test_generate_accepts_new_params(client, sample_pdf_bytes):
    client.post("/api/upload", files={"file": ("test.pdf", sample_pdf_bytes, "application/pdf")})
    r = client.get(
        "/api/generate?out_w=21&out_h=29.7&margin=1.5&spacing=50&marker=1"
        "&border=true&frame_mm=1&frame_color=gray&cross_mm=1.2"
    )
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"


def test_generate_no_session(client):
    from fastapi.testclient import TestClient
    from web.sessions import SessionStore
    import os
    os.environ["BANNER_SESSIONS_DIR"] = "/tmp/banner-eyelets-nosession2"
    fresh_app = create_app(SessionStore())
    fresh_client = TestClient(fresh_app, raise_server_exceptions=False)
    r = fresh_client.get("/api/generate?out_w=21&out_h=29.7")
    assert r.status_code == 401


def test_index_returns_html(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]

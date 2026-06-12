import pytest
import fitz
from pathlib import Path


@pytest.fixture
def sample_pdf(tmp_path) -> Path:
    """Minimal 1-page A4 PDF (595.28×841.89 pt ≈ 21.0×29.7 cm)."""
    doc = fitz.open()
    doc.new_page(width=595.28, height=841.89)
    path = tmp_path / "sample.pdf"
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    doc = fitz.open()
    doc.new_page(width=595.28, height=841.89)
    data = doc.tobytes()
    doc.close()
    return data

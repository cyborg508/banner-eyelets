import pytest
import fitz
from pathlib import Path
from banner_eyelets.models import BannerSpec, RenderConfig
from banner_eyelets.pdf_ops import generate_annotated_pdf


@pytest.fixture
def basic_spec():
    return BannerSpec(
        input_width_cm=21.0, input_height_cm=29.7,
        output_width_cm=21.0, output_height_cm=29.7,
    )


@pytest.fixture
def basic_render():
    return RenderConfig(
        scaled_margin_cm=1.5,
        scaled_spacing_cm=50.0,
        scaled_marker_size_cm=1.0,
        scaled_wrap_cm=0.0,
        final_width_cm=21.0,
        final_height_cm=29.7,
    )


def test_generate_returns_valid_pdf(sample_pdf, basic_spec, basic_render):
    result = generate_annotated_pdf(sample_pdf, basic_spec, basic_render)
    assert isinstance(result, bytes)
    assert result[:4] == b"%PDF"


def test_generate_output_page_size(sample_pdf, basic_spec, basic_render):
    result = generate_annotated_pdf(sample_pdf, basic_spec, basic_render)
    doc = fitz.open("pdf", result)
    page = doc[0]
    from banner_eyelets.geometry import cm_to_pt
    assert abs(page.rect.width - cm_to_pt(21.0)) < 1.0
    assert abs(page.rect.height - cm_to_pt(29.7)) < 1.0
    doc.close()


def test_generate_with_wrap_expands_page(sample_pdf, basic_spec):
    render = RenderConfig(
        scaled_margin_cm=1.5,
        scaled_spacing_cm=50.0,
        scaled_marker_size_cm=1.0,
        scaled_wrap_cm=3.0,
        final_width_cm=27.0,   # 21 + 2*3
        final_height_cm=35.7,  # 29.7 + 2*3
    )
    result = generate_annotated_pdf(sample_pdf, basic_spec, render, wrap=True)
    doc = fitz.open("pdf", result)
    page = doc[0]
    from banner_eyelets.geometry import cm_to_pt
    assert abs(page.rect.width - cm_to_pt(27.0)) < 1.0
    doc.close()


def test_generate_no_qt_dependency():
    """generate_annotated_pdf must not import PySide6."""
    import sys
    for key in list(sys.modules.keys()):
        if "PySide6" in key:
            del sys.modules[key]
    import banner_eyelets.pdf_ops  # should not raise ImportError for PySide6

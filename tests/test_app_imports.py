import pytest


def test_banner_eyelets_importable_without_qt():
    """Package-level imports must not drag in PySide6."""
    from banner_eyelets.geometry import cm_to_pt, pt_to_cm, build_eyelet_points
    from banner_eyelets.models import BannerSpec, RenderConfig, DEFAULT_SETTINGS
    from banner_eyelets.pdf_ops import generate_annotated_pdf
    assert cm_to_pt(2.54) == pytest.approx(72.0, abs=1e-4)

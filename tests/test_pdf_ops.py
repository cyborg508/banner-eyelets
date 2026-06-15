import pytest
import fitz
from pathlib import Path
from banner_eyelets.geometry import cm_to_pt
from banner_eyelets.models import BannerSpec, RenderConfig
from banner_eyelets.pdf_ops import generate_annotated_pdf, frame_color_tuple, centered_rect


def test_centered_rect_centers_content():
    r = centered_rect(0.0, 0.0, 100.0, 100.0, 40.0, 60.0)
    assert (r.x0, r.y0, r.x1, r.y1) == (30.0, 20.0, 70.0, 80.0)


def test_centered_rect_with_offset():
    r = centered_rect(10.0, 5.0, 100.0, 100.0, 100.0, 100.0)
    assert (r.x0, r.y0, r.x1, r.y1) == (10.0, 5.0, 110.0, 105.0)


def _red_source(tmp_path):
    doc = fitz.open()
    page = doc.new_page(width=300.0, height=300.0)
    page.draw_rect(page.rect, color=(1, 0, 0), fill=(1, 0, 0))
    path = tmp_path / "red.pdf"
    doc.save(str(path))
    doc.close()
    return path


def _red_fraction(pdf_bytes):
    doc = fitz.open("pdf", pdf_bytes)
    pix = doc[0].get_pixmap()
    xs, ys = [], []
    for y in range(pix.height):
        for x in range(pix.width):
            r, g, b = pix.pixel(x, y)
            if r > 200 and g < 80 and b < 80:
                xs.append(x)
                ys.append(y)
    doc.close()
    assert xs, "brak czerwieni w wyniku"
    return (
        (max(xs) - min(xs)) / pix.width,
        (max(ys) - min(ys)) / pix.height,
        min(xs) / pix.width,
    )


def _square_render(scaled_w_cm, scaled_h_cm, tmp_path):
    src = _red_source(tmp_path)
    spec = BannerSpec(input_width_cm=10.0, input_height_cm=10.0,
                      output_width_cm=10.0, output_height_cm=10.0)
    render = RenderConfig(scaled_margin_cm=1.5, scaled_spacing_cm=50.0,
                          scaled_marker_size_cm=1.0, scaled_wrap_cm=0.0,
                          final_width_cm=10.0, final_height_cm=10.0)
    return generate_annotated_pdf(src, spec, render,
                                  artwork_width_cm=scaled_w_cm,
                                  artwork_height_cm=scaled_h_cm)


def test_artwork_scaled_smaller_is_centered(tmp_path):
    w_frac, h_frac, left_frac = _red_fraction(_square_render(5.0, 5.0, tmp_path))
    assert 0.45 < w_frac < 0.55, w_frac      # 5cm z 10cm ≈ połowa
    assert 0.45 < h_frac < 0.55, h_frac
    assert 0.2 < left_frac < 0.3, left_frac  # wyśrodkowane: margines ≈ 25%


def test_artwork_default_none_fills_input(tmp_path):
    src = _red_source(tmp_path)
    spec = BannerSpec(input_width_cm=10.0, input_height_cm=10.0,
                      output_width_cm=10.0, output_height_cm=10.0)
    render = RenderConfig(scaled_margin_cm=1.5, scaled_spacing_cm=50.0,
                          scaled_marker_size_cm=1.0, scaled_wrap_cm=0.0,
                          final_width_cm=10.0, final_height_cm=10.0)
    pdf = generate_annotated_pdf(src, spec, render)  # bez skalowania
    w_frac, h_frac, _ = _red_fraction(pdf)
    assert w_frac > 0.9 and h_frac > 0.9      # wejście=wyjście → wypełnia arkusz


def test_frame_color_tuple_basic():
    assert frame_color_tuple("black") == (0.0, 0.0, 0.0)
    assert frame_color_tuple("white") == (1.0, 1.0, 1.0)
    assert frame_color_tuple("gray") == (0.5, 0.5, 0.5)


def test_frame_color_tuple_cmyk():
    # C / M / Y as true CMYK 4-tuples
    assert frame_color_tuple("c") == (1.0, 0.0, 0.0, 0.0)
    assert frame_color_tuple("m") == (0.0, 1.0, 0.0, 0.0)
    assert frame_color_tuple("y") == (0.0, 0.0, 1.0, 0.0)


def test_frame_color_tuple_unknown_defaults_gray():
    assert frame_color_tuple("nonsense") == (0.5, 0.5, 0.5)


def test_generate_accepts_new_thickness_params(sample_pdf, basic_spec, basic_render):
    result = generate_annotated_pdf(
        sample_pdf,
        basic_spec,
        basic_render,
        border=True,
        frame_line_width_pt=2.8,
        frame_color=(1.0, 0.0, 0.0, 0.0),
        cross_line_width_pt=3.4,
    )
    assert isinstance(result, bytes)
    assert result[:4] == b"%PDF"


def test_frame_is_single_colored_line(sample_pdf, basic_spec):
    """Obramówka = jedna linia w zadanym kolorze; BEZ czarnej linii na wierzchu."""
    render = RenderConfig(
        scaled_margin_cm=1.5, scaled_spacing_cm=50.0, scaled_marker_size_cm=1.0,
        scaled_wrap_cm=3.0, final_width_cm=27.0, final_height_cm=35.7,
    )
    pdf = generate_annotated_pdf(
        sample_pdf, basic_spec, render, wrap=True,
        frame_line_width_pt=cm_to_pt(0.3),  # ~3mm, dobrze widoczna
        frame_color=(1.0, 0.0, 0.0, 0.0),  # cyan CMYK
    )
    doc = fitz.open("pdf", pdf)
    pix = doc[0].get_pixmap(matrix=fitz.Matrix(4, 4))
    x = pix.width // 2
    # pasmo ramki wewnętrznej (wrap 3cm na 35.7cm) ~ 8–9% wysokości od góry
    band = [pix.pixel(x, y) for y in range(int(pix.height * 0.07), int(pix.height * 0.11))]
    nonwhite = [px for px in band if px != (255, 255, 255)]
    assert nonwhite, "Ramka nie została narysowana w spodziewanym pasmie"
    # jest cyan (niski R, wysoki B)
    assert any(r < 80 and b > 150 for r, g, b in nonwhite), f"Brak cyan w ramce: {nonwhite}"
    # NIE ma czarnego rdzenia (pojedyncza linia, nie halo+czarna)
    assert not any(r < 30 and g < 30 and b < 30 for r, g, b in nonwhite), \
        f"Ramka ma czarny rdzeń (powinna być jedną linią): {nonwhite}"
    doc.close()


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

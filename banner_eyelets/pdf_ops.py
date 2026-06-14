from __future__ import annotations

from pathlib import Path
from typing import List, Sequence, Tuple

import fitz

from banner_eyelets.geometry import cm_to_pt, build_eyelet_points
from banner_eyelets.models import BannerSpec, RenderConfig

# Otoczka (halo) krzyżyka jest dwukrotnie szersza niż jego linia — zachowane
# z oryginalnych mnożników (0.32 / 0.16 = 2.0).
CROSS_HALO_RATIO = 2.0

# Nazwa koloru obwódki → krotka koloru dla PyMuPDF.
# 1 element = skala szarości, 3 = RGB, 4 = CMYK.
FRAME_COLORS: dict[str, Tuple[float, ...]] = {
    "black": (0.0, 0.0, 0.0),
    "white": (1.0, 1.0, 1.0),
    "gray": (0.5, 0.5, 0.5),
    "c": (1.0, 0.0, 0.0, 0.0),
    "m": (0.0, 1.0, 0.0, 0.0),
    "y": (0.0, 0.0, 1.0, 0.0),
}


def frame_color_tuple(name: str) -> Tuple[float, ...]:
    """Zamień nazwę koloru obwódki na krotkę koloru. Nieznane → szary."""
    return FRAME_COLORS.get((name or "").strip().lower(), FRAME_COLORS["gray"])


def draw_cross(
    page: fitz.Page,
    x_pt: float,
    y_pt: float,
    size_pt: float,
    outline_multiplier: float,
    inner_multiplier: float,
    line_width_pt: float | None = None,
) -> None:
    half = size_pt / 2.0
    if line_width_pt is not None:
        inner_width = max(2.0, line_width_pt)
        outline_width = max(5.5, line_width_pt * CROSS_HALO_RATIO)
    else:
        outline_width = max(5.5, size_pt * outline_multiplier)
        inner_width = max(2.0, size_pt * inner_multiplier)
    shape = page.new_shape()
    shape.draw_line(fitz.Point(x_pt - half, y_pt), fitz.Point(x_pt + half, y_pt))
    shape.draw_line(fitz.Point(x_pt, y_pt - half), fitz.Point(x_pt, y_pt + half))
    shape.finish(color=(1, 1, 1), width=outline_width)
    shape.draw_line(fitz.Point(x_pt - half, y_pt), fitz.Point(x_pt + half, y_pt))
    shape.draw_line(fitz.Point(x_pt, y_pt - half), fitz.Point(x_pt, y_pt + half))
    shape.finish(color=(0, 0, 0), width=inner_width)
    shape.commit()


def draw_frame(
    page: fitz.Page,
    rect: fitz.Rect,
    base_width_pt: float = 2.4,
    line_width_pt: float | None = None,
    halo_width_pt: float | None = None,
    halo_color: Sequence[float] = (1.0, 1.0, 1.0),
) -> None:
    if line_width_pt is not None:
        # granica obrysu = czarna linia; obwódka = otoczka po każdej stronie linii.
        inner_width = max(2.0, line_width_pt)
        halo = halo_width_pt if halo_width_pt is not None else 0.0
        outline_width = max(5.5, inner_width + 2.0 * halo)
    else:
        outline_width = max(5.5, base_width_pt * 2.2)
        inner_width = max(2.0, base_width_pt)
    shape = page.new_shape()
    shape.draw_rect(rect)
    shape.finish(color=tuple(halo_color), width=outline_width)
    shape.draw_rect(rect)
    shape.finish(color=(0, 0, 0), width=inner_width)
    shape.commit()


def generate_annotated_pdf(
    src_path: Path,
    spec: BannerSpec,
    render_cfg: RenderConfig,
    border: bool = False,
    wrap: bool = False,
    frame_base_width_pt: float = 2.4,
    cross_outline_multiplier: float = 0.32,
    cross_inner_multiplier: float = 0.16,
    frame_line_width_pt: float | None = None,
    frame_halo_width_pt: float | None = None,
    frame_halo_color: Sequence[float] = (1.0, 1.0, 1.0),
    cross_line_width_pt: float | None = None,
) -> bytes:
    src_doc = fitz.open(str(src_path))

    base_output_width_pt = cm_to_pt(spec.output_width_cm)
    base_output_height_pt = cm_to_pt(spec.output_height_cm)
    input_width_pt = cm_to_pt(spec.input_width_cm)
    input_height_pt = cm_to_pt(spec.input_height_cm)
    wrap_margin_pt = cm_to_pt(render_cfg.scaled_wrap_cm)
    final_width_pt = cm_to_pt(render_cfg.final_width_cm)
    final_height_pt = cm_to_pt(render_cfg.final_height_cm)

    dst_doc = fitz.open()
    dst_page = dst_doc.new_page(width=final_width_pt, height=final_height_pt)

    base_left = wrap_margin_pt
    base_top = wrap_margin_pt
    base_right = base_left + base_output_width_pt
    base_bottom = base_top + base_output_height_pt

    offset_x = base_left + (base_output_width_pt - input_width_pt) / 2.0
    offset_y = base_top + (base_output_height_pt - input_height_pt) / 2.0
    target_rect = fitz.Rect(
        offset_x, offset_y,
        offset_x + input_width_pt,
        offset_y + input_height_pt,
    )
    dst_page.show_pdf_page(target_rect, src_doc, 0, keep_proportion=False, overlay=False)

    if border or wrap:
        inner_rect = fitz.Rect(base_left, base_top, base_right, base_bottom)
        draw_frame(
            dst_page, inner_rect, frame_base_width_pt,
            line_width_pt=frame_line_width_pt,
            halo_width_pt=frame_halo_width_pt,
            halo_color=frame_halo_color,
        )
        if wrap:
            outer_rect = fitz.Rect(0, 0, final_width_pt, final_height_pt)
            draw_frame(
                dst_page, outer_rect, frame_base_width_pt,
                line_width_pt=frame_line_width_pt,
                halo_width_pt=frame_halo_width_pt,
                halo_color=frame_halo_color,
            )

    points_cm = build_eyelet_points(
        spec.output_width_cm,
        spec.output_height_cm,
        render_cfg.scaled_margin_cm,
        render_cfg.scaled_spacing_cm,
    )
    marker_pt = cm_to_pt(render_cfg.scaled_marker_size_cm)
    for x_cm, y_cm in points_cm:
        x_pt = base_left + cm_to_pt(x_cm)
        y_pt = base_top + base_output_height_pt - cm_to_pt(y_cm)
        draw_cross(
            dst_page, x_pt, y_pt, marker_pt,
            cross_outline_multiplier, cross_inner_multiplier,
            line_width_pt=cross_line_width_pt,
        )

    result = dst_doc.tobytes()
    dst_doc.close()
    src_doc.close()
    return result

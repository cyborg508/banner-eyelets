import math
import pytest
from banner_eyelets.geometry import (
    cm_to_pt,
    pt_to_cm,
    evenly_spaced_positions,
    build_eyelet_points,
    POINTS_PER_CM,
)


def test_cm_to_pt_round_trip():
    assert abs(pt_to_cm(cm_to_pt(10.0)) - 10.0) < 1e-9


def test_cm_to_pt_known_value():
    # 2.54 cm == 1 inch == 72 pt
    assert abs(cm_to_pt(2.54) - 72.0) < 1e-6


def test_points_per_cm_constant():
    assert abs(POINTS_PER_CM - 72.0 / 2.54) < 1e-9


def test_evenly_spaced_inner_zero():
    # length == 2*margin → inner == 0 → one point at margin
    result = evenly_spaced_positions(3.0, 1.5, 50.0)
    assert result == [1.5]


def test_evenly_spaced_basic():
    # 100 cm banner, 1.5 cm margin → inner 97 cm, target 50 → 2 segments → 3 points
    result = evenly_spaced_positions(100.0, 1.5, 50.0)
    assert len(result) == 3
    assert abs(result[0] - 1.5) < 1e-9
    assert abs(result[-1] - 98.5) < 1e-9
    # equal spacing
    assert abs(result[1] - result[0] - (result[2] - result[1])) < 1e-9


def test_evenly_spaced_negative_margin_raises():
    with pytest.raises(ValueError, match="Margines"):
        evenly_spaced_positions(1.0, 2.0, 50.0)


def test_build_eyelet_points_corners():
    points = build_eyelet_points(100.0, 50.0, 1.5, 50.0)
    corners = [(1.5, 1.5), (1.5, 48.5), (98.5, 1.5), (98.5, 48.5)]
    for cx, cy in corners:
        assert any(
            abs(px - cx) < 1e-6 and abs(py - cy) < 1e-6 for px, py in points
        ), f"Missing corner ({cx}, {cy})"


def test_build_eyelet_points_unique():
    points = build_eyelet_points(100.0, 50.0, 1.5, 50.0)
    seen: set = set()
    for x, y in points:
        key = (round(x, 6), round(y, 6))
        assert key not in seen, f"Duplicate point {key}"
        seen.add(key)


def test_build_eyelet_points_count_small_banner():
    # 3×3 cm banner, 1.5 cm margin → inner 0 on both axes → xs=[1.5], ys=[1.5]
    # top: (1.5,1.5), bottom: (1.5,1.5) → deduplicated to 1 unique
    # ys[1:-1] is empty → no side points
    points = build_eyelet_points(3.0, 3.0, 1.5, 50.0)
    assert len(points) == 1

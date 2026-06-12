from __future__ import annotations

import math
from typing import List, Tuple

CM_PER_INCH = 2.54
POINTS_PER_INCH = 72.0
POINTS_PER_CM = POINTS_PER_INCH / CM_PER_INCH


def cm_to_pt(value_cm: float) -> float:
    return value_cm * POINTS_PER_CM


def pt_to_cm(value_pt: float) -> float:
    return value_pt / POINTS_PER_CM


def evenly_spaced_positions(
    length_cm: float, margin_cm: float, target_spacing_cm: float
) -> List[float]:
    inner = length_cm - 2 * margin_cm
    if inner < 0:
        raise ValueError("Margines jest większy niż połowa długości boku.")
    if math.isclose(inner, 0.0, abs_tol=1e-9):
        return [margin_cm]
    segments = max(1, round(inner / target_spacing_cm))
    step = inner / segments
    return [margin_cm + i * step for i in range(segments + 1)]


def build_eyelet_points(
    output_width_cm: float,
    output_height_cm: float,
    margin_cm: float,
    spacing_cm: float,
) -> List[Tuple[float, float]]:
    xs = evenly_spaced_positions(output_width_cm, margin_cm, spacing_cm)
    ys = evenly_spaced_positions(output_height_cm, margin_cm, spacing_cm)

    points: List[Tuple[float, float]] = []
    for x in xs:
        points.append((x, margin_cm))
        points.append((x, output_height_cm - margin_cm))
    for y in ys[1:-1]:
        points.append((margin_cm, y))
        points.append((output_width_cm - margin_cm, y))

    unique: List[Tuple[float, float]] = []
    seen: set = set()
    for x, y in points:
        key = (round(x, 6), round(y, 6))
        if key not in seen:
            seen.add(key)
            unique.append((x, y))
    return unique

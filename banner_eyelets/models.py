from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class BannerSpec:
    input_width_cm: float
    input_height_cm: float
    output_width_cm: float
    output_height_cm: float
    margin_cm: float = 1.5
    target_spacing_cm: float = 50.0
    marker_size_cm: float = 1.0


@dataclass
class RenderConfig:
    scaled_margin_cm: float
    scaled_spacing_cm: float
    scaled_marker_size_cm: float
    scaled_wrap_cm: float
    final_width_cm: float
    final_height_cm: float
    scale_mode_label: str = "100%"


DEFAULT_SETTINGS: Dict[str, Any] = {
    "margin_cm": 1.5,
    "spacing_cm": 50.0,
    "marker_size_cm": 1.0,
    "wrap_extra_cm": 3.0,
    "frame_base_width_pt": 2.4,
    "cross_outline_multiplier": 0.32,
    "cross_inner_multiplier": 0.16,
    "frame_mm": 1.0,
    "frame_color": "gray",
    "cross_mm": 1.2,
    "border_enabled": False,
    "wrap_enabled": False,
    "half_scale_enabled": False,
}

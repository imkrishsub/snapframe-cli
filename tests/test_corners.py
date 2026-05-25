# tests/test_corners.py
from __future__ import annotations

import pytest
from PIL import Image

from snapframe.config import DeviceFrameTransformConfig
from snapframe.renderer import (
    _FLOAT_PERSPECTIVE_FACTOR,
    _ISO_COS,
    _ISO_SIN,
    _apply_tilt,
    projected_corners,
)


def test_none_returns_bounding_box():
    cfg = DeviceFrameTransformConfig(mode="none")
    corners = projected_corners(cfg, 300, 600, 300, 600, 10, 20)
    assert corners == [(10, 20), (310, 20), (310, 620), (10, 620)]


def test_tilt_zero_same_as_none():
    cfg = DeviceFrameTransformConfig(mode="tilt", tilt_angle=0.0)
    img = Image.new("RGBA", (300, 600))
    post = _apply_tilt(img, 0.0)
    corners = projected_corners(cfg, 300, 600, post.width, post.height, 0, 0)
    none_cfg = DeviceFrameTransformConfig(mode="none")
    expected = projected_corners(none_cfg, 300, 600, post.width, post.height, 0, 0)
    for i, ((cx, cy), (ex, ey)) in enumerate(zip(corners, expected)):
        assert abs(cx - ex) < 1, f"corner {i} x mismatch"
        assert abs(cy - ey) < 1, f"corner {i} y mismatch"


def test_tilt_90_tl_and_tr_share_x():
    # After 90° clockwise tilt the top edge becomes vertical — TL and TR share x
    cfg = DeviceFrameTransformConfig(mode="tilt", tilt_angle=90.0)
    img = Image.new("RGBA", (300, 600))
    post = _apply_tilt(img, 90.0)
    corners = projected_corners(cfg, 300, 600, post.width, post.height, 0, 0)
    assert abs(corners[0][0] - corners[1][0]) < 2


def test_iso_left_tl_x_equals_pre_h_times_sin30():
    cfg = DeviceFrameTransformConfig(mode="iso", iso_variant="left")
    corners = projected_corners(cfg, 300, 600, 0, 0, 0, 0)  # post_w/post_h unused by iso transform
    assert corners[0][0] == int(600 * _ISO_SIN)


def test_iso_left_tr_x_equals_pre_w_plus_pre_h_times_sin30():
    cfg = DeviceFrameTransformConfig(mode="iso", iso_variant="left")
    corners = projected_corners(cfg, 300, 600, 0, 0, 0, 0)  # post_w/post_h unused by iso transform
    assert abs(corners[1][0] - (300 + 600 * _ISO_SIN)) < 0.01


def test_iso_right_tl_is_at_origin():
    cfg = DeviceFrameTransformConfig(mode="iso", iso_variant="right")
    corners = projected_corners(cfg, 300, 600, 0, 0, 0, 0)
    assert abs(corners[0][0]) < 0.01
    assert abs(corners[0][1]) < 0.01


def test_iso_right_bl_x_equals_pre_h_times_sin30():
    cfg = DeviceFrameTransformConfig(mode="iso", iso_variant="right")
    corners = projected_corners(cfg, 300, 600, 0, 0, 0, 0)  # post_w/post_h unused by iso transform
    assert corners[3][0] == int(600 * _ISO_SIN)


def test_float_left_lean_tl_y_equals_factor_half_times_post_h():
    cfg = DeviceFrameTransformConfig(mode="float", float_preset="left-lean")
    corners = projected_corners(cfg, 300, 600, 300, 600, 0, 0)
    expected_y = _FLOAT_PERSPECTIVE_FACTOR / 2 * 600
    assert abs(corners[0][1] - expected_y) < 0.01


def test_float_left_lean_tr_is_at_top():
    cfg = DeviceFrameTransformConfig(mode="float", float_preset="left-lean")
    corners = projected_corners(cfg, 300, 600, 300, 600, 0, 0)
    assert abs(corners[1][1]) < 0.01  # TR y == 0


def test_float_right_lean_tr_y_equals_factor_half_times_post_h():
    cfg = DeviceFrameTransformConfig(mode="float", float_preset="right-lean")
    corners = projected_corners(cfg, 300, 600, 300, 600, 0, 0)
    expected_y = _FLOAT_PERSPECTIVE_FACTOR / 2 * 600
    assert abs(corners[1][1] - expected_y) < 0.01


def test_float_right_lean_tl_is_at_top():
    cfg = DeviceFrameTransformConfig(mode="float", float_preset="right-lean")
    corners = projected_corners(cfg, 300, 600, 300, 600, 0, 0)
    assert abs(corners[0][1]) < 0.01  # TL y == 0


def test_all_modes_return_four_corners():
    cases = [
        DeviceFrameTransformConfig(mode="none"),
        DeviceFrameTransformConfig(mode="tilt", tilt_angle=15.0),
        DeviceFrameTransformConfig(mode="iso", iso_variant="left"),
        DeviceFrameTransformConfig(mode="iso", iso_variant="right"),
        DeviceFrameTransformConfig(mode="float", float_preset="left-lean"),
        DeviceFrameTransformConfig(mode="float", float_preset="right-lean"),
    ]
    for cfg in cases:
        result = projected_corners(cfg, 200, 400, 200, 400, 5, 10)
        assert len(result) == 4, f"expected 4 corners for mode={cfg.mode}"


@pytest.mark.parametrize("cfg", [
    DeviceFrameTransformConfig(mode="none"),
    DeviceFrameTransformConfig(mode="iso", iso_variant="left"),
    DeviceFrameTransformConfig(mode="float", float_preset="left-lean"),
])
def test_corners_offset_by_dev_x_dev_y(cfg):
    c1 = projected_corners(cfg, 300, 600, 300, 600, 0, 0)
    c2 = projected_corners(cfg, 300, 600, 300, 600, 50, 30)
    for i, ((x1, y1), (x2, y2)) in enumerate(zip(c1, c2)):
        assert abs((x2 - x1) - 50) < 0.01, f"corner {i} x offset wrong for {cfg.mode}"
        assert abs((y2 - y1) - 30) < 0.01, f"corner {i} y offset wrong for {cfg.mode}"

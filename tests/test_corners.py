# tests/test_corners.py
from __future__ import annotations

import pytest
from PIL import Image

from snaphaus.config import DeviceFrameTransformConfig
from snaphaus.renderer import (
    _ISO_COS,
    _ISO_SIN,
    _apply_tilt,
    _iso_scale,
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


def test_tilt_90_tl_is_at_right_edge():
    # After CW 90°, the original TL corner moves to the right edge of the output.
    # This verifies the rotation direction (not just that TL/TR share x, which
    # passes regardless of whether the angle is mirrored).
    cfg = DeviceFrameTransformConfig(mode="tilt", tilt_angle=90.0)
    img = Image.new("RGBA", (300, 600))
    post = _apply_tilt(img, 90.0)
    corners = projected_corners(cfg, 300, 600, post.width, post.height, 0, 0)
    # TL must be near (post_w, 0), not near (0, post_h)
    assert abs(corners[0][0] - post.width) < 2, f"TL.x should be ~{post.width}, got {corners[0][0]}"
    assert abs(corners[0][1]) < 2, f"TL.y should be ~0, got {corners[0][1]}"


def test_tilt_minus15_tr_is_higher_than_tl():
    # Default tilt_angle=-15 visually leans the device: the top-right corner rises
    # (y decreases) while top-left shifts down slightly.  TR.y < TL.y.
    cfg = DeviceFrameTransformConfig(mode="tilt", tilt_angle=-15.0)
    img = Image.new("RGBA", (300, 600))
    post = _apply_tilt(img, -15.0)
    corners = projected_corners(cfg, 300, 600, post.width, post.height, 0, 0)
    tl_y = corners[0][1]
    tr_y = corners[1][1]
    assert tr_y < tl_y, f"With tilt_angle=-15, TR.y ({tr_y:.1f}) should be less than TL.y ({tl_y:.1f})"


def _approx_corners(actual, expected):
    for i, ((ax, ay), (ex, ey)) in enumerate(zip(actual, expected)):
        assert abs(ax - ex) < 0.01 and abs(ay - ey) < 0.01, f"corner {i}: {(ax, ay)} != {(ex, ey)}"


def test_iso_left_corners():
    cfg = DeviceFrameTransformConfig(mode="iso", iso_variant="left")
    corners = projected_corners(cfg, 300, 600, 0, 0, 0, 0)  # post_w/post_h unused by iso transform
    k = _iso_scale(300, 600)
    dx, dy, e = k * 300 * _ISO_COS, k * 300 * _ISO_SIN, k * 600
    _approx_corners(corners, [(0, 0), (dx, dy), (dx, dy + e), (0, e)])


def test_iso_right_corners():
    cfg = DeviceFrameTransformConfig(mode="iso", iso_variant="right")
    corners = projected_corners(cfg, 300, 600, 0, 0, 0, 0)  # post_w/post_h unused by iso transform
    k = _iso_scale(300, 600)
    dx, dy, e = k * 300 * _ISO_COS, k * 300 * _ISO_SIN, k * 600
    _approx_corners(corners, [(0, dy), (dx, 0), (dx, e), (0, dy + e)])


@pytest.mark.parametrize("variant", ["left", "right"])
def test_iso_vertical_edges_stay_vertical(variant):
    cfg = DeviceFrameTransformConfig(mode="iso", iso_variant=variant)
    tl, tr, br, bl = projected_corners(cfg, 300, 600, 0, 0, 0, 0)
    assert abs(tl[0] - bl[0]) < 0.01 and abs(tr[0] - br[0]) < 0.01


@pytest.mark.parametrize("variant", ["left", "right"])
def test_iso_fits_pre_transform_height(variant):
    cfg = DeviceFrameTransformConfig(mode="iso", iso_variant=variant)
    corners = projected_corners(cfg, 300, 600, 0, 0, 0, 0)
    ys = [y for _, y in corners]
    assert abs((max(ys) - min(ys)) - 600) < 0.01


@pytest.mark.parametrize("variant", ["left", "right"])
def test_iso_horizontal_edges_follow_30_degree_axis(variant):
    import math
    cfg = DeviceFrameTransformConfig(mode="iso", iso_variant=variant)
    tl, tr, _, _ = projected_corners(cfg, 300, 600, 0, 0, 0, 0)
    angle = math.degrees(math.atan2(abs(tr[1] - tl[1]), tr[0] - tl[0]))
    assert abs(angle - 30) < 0.01
    tl, tr, br, bl = projected_corners(cfg, 300, 600, 0, 0, 0, 0)
    width = math.hypot(tr[0] - tl[0], tr[1] - tl[1])
    height = math.hypot(bl[0] - tl[0], bl[1] - tl[1])
    assert abs(width / height - 300 / 600) < 0.001  # aspect preserved along iso axes


@pytest.mark.parametrize("variant", ["left", "right"])
def test_iso_corners_match_rendered_pixels(variant):
    from snaphaus.renderer import _apply_iso
    img = Image.new("RGBA", (300, 600), (255, 0, 0, 255))
    out = _apply_iso(img, variant)
    cfg = DeviceFrameTransformConfig(mode="iso", iso_variant=variant)
    corners = projected_corners(cfg, 300, 600, *out.size, 0, 0)
    cx = sum(x for x, _ in corners) / 4
    cy = sum(y for _, y in corners) / 4
    for x, y in corners:
        # Step 5 % towards the centroid: must be opaque (inside the device)
        px = int(x + (cx - x) * 0.05)
        py = int(y + (cy - y) * 0.05)
        assert out.getpixel((px, py))[3] == 255, f"expected opaque at {(px, py)}"
    # Opposite canvas corners outside the face must be transparent
    if variant == "left":
        assert out.getpixel((out.width - 2, 1))[3] == 0
        assert out.getpixel((1, out.height - 2))[3] == 0
    else:
        assert out.getpixel((1, 1))[3] == 0
        assert out.getpixel((out.width - 2, out.height - 2))[3] == 0


def _float(preset, w=300, h=600):
    cfg = DeviceFrameTransformConfig(mode="float", float_preset=preset)
    return projected_corners(cfg, w, h, 0, 0, 0, 0)  # post_w/post_h unused by float transform


def test_float_left_lean_near_right_edge_is_full_height():
    tl, tr, br, bl = _float("left-lean")
    assert abs(tr[0] - br[0]) < 0.01
    assert abs(tr[1]) < 0.01 and abs(br[1] - 600) < 0.01


def test_float_left_lean_far_left_edge_is_shorter_and_centred():
    tl, tr, br, bl = _float("left-lean")
    assert abs(tl[0]) < 0.01 and abs(bl[0]) < 0.01
    far = bl[1] - tl[1]
    assert 0.75 * 600 < far < 0.95 * 600
    assert abs((tl[1] + bl[1]) / 2 - 300) < 0.01


def test_float_width_is_foreshortened():
    import math
    for preset in ("left-lean", "right-lean"):
        xs = [x for x, _ in _float(preset)]
        assert max(xs) - min(xs) < 300 * math.cos(math.radians(20))


def test_float_right_lean_mirrors_left_lean():
    left = _float("left-lean")
    right = _float("right-lean")
    out_w = max(x for x, _ in left)
    # mirror x and swap left/right corners: TL<->TR, BL<->BR
    mirrored = [(out_w - x, y) for x, y in [left[1], left[0], left[3], left[2]]]
    for (ax, ay), (ex, ey) in zip(right, mirrored):
        assert abs(ax - ex) < 0.01 and abs(ay - ey) < 0.01


@pytest.mark.parametrize("preset", ["left-lean", "right-lean"])
def test_float_corners_match_rendered_pixels(preset):
    from snaphaus.renderer import _apply_float
    img = Image.new("RGBA", (300, 600), (255, 0, 0, 255))
    out = _apply_float(img, preset)
    corners = _float(preset)
    cx = sum(x for x, _ in corners) / 4
    cy = sum(y for _, y in corners) / 4
    for x, y in corners:
        px = int(x + (cx - x) * 0.05)
        py = int(y + (cy - y) * 0.05)
        assert out.getpixel((px, py))[3] == 255, f"expected opaque at {(px, py)}"


def test_solve_perspective_maps_dst_to_src():
    from snaphaus.renderer import _solve_perspective
    dst = [(0, 30), (170, 0), (170, 600), (0, 570)]
    src = [(0, 0), (300, 0), (300, 600), (0, 600)]
    a, b, c, d, e, f, g, h = _solve_perspective(dst, src)
    for (x, y), (u, v) in zip(dst, src):
        den = g * x + h * y + 1
        assert abs((a * x + b * y + c) / den - u) < 1e-6
        assert abs((d * x + e * y + f) / den - v) < 1e-6


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

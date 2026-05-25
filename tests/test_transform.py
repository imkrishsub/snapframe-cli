import math

import pytest
from PIL import Image

from snapframe.config import DeviceFrameTransformConfig
from snapframe.renderer import _apply_tilt, _apply_iso, _apply_float, apply_transform


def _rgba(w, h):
    return Image.new("RGBA", (w, h), (200, 100, 50, 255))


# ── _apply_tilt ───────────────────────────────────────────────────────────────

def test_apply_tilt_returns_rgba():
    result = _apply_tilt(_rgba(100, 200), 15.0)
    assert result.mode == "RGBA"


def test_apply_tilt_expands_canvas():
    img = _rgba(100, 200)
    result = _apply_tilt(img, 15.0)
    assert result.width > 100 or result.height > 200


def test_apply_tilt_zero_angle_preserves_size():
    img = _rgba(100, 200)
    result = _apply_tilt(img, 0.0)
    assert result.size == (100, 200)


def test_apply_tilt_positive_negative_same_size():
    img = _rgba(100, 200)
    pos = _apply_tilt(img, 15.0)
    neg = _apply_tilt(img, -15.0)
    assert pos.size == neg.size


# ── _apply_iso ────────────────────────────────────────────────────────────────

def test_apply_iso_left_returns_rgba():
    result = _apply_iso(_rgba(100, 200), "left")
    assert result.mode == "RGBA"


def test_apply_iso_wider_than_source():
    result = _apply_iso(_rgba(100, 200), "left")
    assert result.width > 100


def test_apply_iso_shorter_than_source():
    result = _apply_iso(_rgba(100, 200), "left")
    assert result.height < 200


def test_apply_iso_left_and_right_same_size():
    img = _rgba(100, 200)
    assert _apply_iso(img, "left").size == _apply_iso(img, "right").size


def test_apply_iso_output_dimensions():
    img = _rgba(100, 200)
    result = _apply_iso(img, "left")
    expected_w = int(100 + 200 * math.sin(math.radians(30)))
    expected_h = int(200 * math.cos(math.radians(30)))
    assert result.size == (expected_w, expected_h)


# ── _apply_float ──────────────────────────────────────────────────────────────

def test_apply_float_returns_rgba():
    result = _apply_float(_rgba(200, 400), "left-lean")
    assert result.mode == "RGBA"


def test_apply_float_preserves_size():
    img = _rgba(200, 400)
    for preset in ("left-lean", "right-lean"):
        assert _apply_float(img, preset).size == img.size


def test_apply_float_unknown_preset_does_not_raise():
    result = _apply_float(_rgba(200, 400), "nonexistent")
    assert result is not None
    assert result.size == (200, 400)


def test_apply_float_left_lean_has_transparent_top_left_corner():
    # For left-lean, the top-left corner recedes and must be transparent.
    result = _apply_float(_rgba(200, 400), "left-lean")
    assert result.getpixel((0, 0))[3] == 0, "top-left corner should be transparent for left-lean"


def test_apply_float_left_lean_top_right_corner_is_opaque():
    # Right edge faces the viewer — top-right corner should remain opaque.
    result = _apply_float(_rgba(200, 400), "left-lean")
    assert result.getpixel((199, 0))[3] > 0, "top-right corner should be opaque for left-lean"


def test_apply_float_right_lean_has_transparent_top_right_corner():
    # right-lean is the mirror — top-right corner should recede and be transparent.
    result = _apply_float(_rgba(200, 400), "right-lean")
    assert result.getpixel((199, 0))[3] == 0, "top-right corner should be transparent for right-lean"


def test_apply_float_right_lean_top_left_corner_is_opaque():
    result = _apply_float(_rgba(200, 400), "right-lean")
    assert result.getpixel((0, 0))[3] > 0, "top-left corner should be opaque for right-lean"


# ── apply_transform dispatcher ────────────────────────────────────────────────

def test_apply_transform_tilt():
    img = _rgba(200, 400)
    cfg = DeviceFrameTransformConfig(mode="tilt", tilt_angle=30.0)
    result = apply_transform(img, cfg)
    assert result.size != img.size  # expand=True changes size


def test_apply_transform_iso():
    img = _rgba(200, 400)
    cfg = DeviceFrameTransformConfig(mode="iso", iso_variant="left")
    result = apply_transform(img, cfg)
    expected_w = int(200 + 400 * math.sin(math.radians(30)))
    expected_h = int(400 * math.cos(math.radians(30)))
    assert result.size == (expected_w, expected_h)


def test_apply_transform_float():
    img = _rgba(200, 400)
    cfg = DeviceFrameTransformConfig(mode="float", float_preset="left-lean")
    result = apply_transform(img, cfg)
    assert result.size == img.size


def test_apply_transform_none():
    img = _rgba(200, 400)
    cfg = DeviceFrameTransformConfig(mode="none")
    result = apply_transform(img, cfg)
    assert result is img  # no-op returns same object

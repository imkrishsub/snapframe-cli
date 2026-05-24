from pathlib import Path

import pytest

from snapframe.config import ImageConfig, TemplateConfig
from snapframe.renderer import _DEVICE_MIN_SLIVER, _FRAMES_DIR, FINISH_PRESETS, generate_frame, render, render_with_bounds

# Discovered at import time so pytest.mark.parametrize can use it.
ALL_MODELS = sorted(p.stem for p in _FRAMES_DIR.glob("*.toml"))


def test_finish_presets_keys():
    assert set(FINISH_PRESETS.keys()) == {"black", "matte-gray", "natural-titanium"}


def test_finish_presets_have_required_colors():
    for name, preset in FINISH_PRESETS.items():
        assert "border" in preset, f"{name} missing 'border'"
        assert "highlight" in preset, f"{name} missing 'highlight'"
        assert "button" in preset, f"{name} missing 'button'"


def test_generate_frame_returns_rgba():
    img, screen_rect = generate_frame("iphone-16-pro", 400, 800)
    assert img.mode == "RGBA"


def test_generate_frame_respects_target_dimensions():
    img, _ = generate_frame("iphone-16-pro", 400, 800)
    assert img.width <= 400 + 20   # allow a few px for button padding
    assert img.height <= 800


def test_generate_frame_different_finishes_same_size():
    img_black, _ = generate_frame("iphone-16-pro", 400, 800, finish="black")
    img_gray, _ = generate_frame("iphone-16-pro", 400, 800, finish="matte-gray")
    img_titanium, _ = generate_frame("iphone-16-pro", 400, 800, finish="natural-titanium")
    assert img_black.size == img_gray.size == img_titanium.size


def test_generate_frame_unknown_finish_falls_back_to_black():
    # Should not raise; falls back to black preset
    img, _ = generate_frame("iphone-16-pro", 400, 800, finish="nonexistent")
    assert img is not None


def test_generate_frame_ipad_does_not_crash():
    img, _ = generate_frame("ipad-pro-12-9", 800, 1000)
    assert img is not None


def test_dynamic_island_area_is_inside_transparent_screen_cutout():
    """DI pill rendering was removed so the screenshot's native DI shows through cleanly.

    The DI centre sits well inside the screen cutout rectangle, so its alpha
    channel must be 0 — any opaque pixel there would duplicate the DI already
    present in a Simulator screenshot.
    """
    img, _ = generate_frame("iphone-16-pro", 402, 874)
    # scale = 1.0, btn_w = 3
    # DI spec: x=138, w=126 → centre_x = (138 + 3) + 63 = 204
    #          y=14,  h=37  → centre_y = 14 + 18 = 32
    # Screen cutout x∈[17,390], y∈[14,859] — (204,32) is clearly inside.
    pixel = img.getpixel((204, 32))
    assert pixel[3] == 0, "DI area is part of the transparent screen cutout"


def test_generate_frame_image_wider_than_frame_body():
    """Image must be wider than the frame body to include button protrusion."""
    # iphone-16-pro ref: 402×874. At target 400×800: scale = min(400/402, 800/874) ≈ 0.915
    # fw = int(402 * 0.915) = 367; btn_w = max(2, int(3 * 0.915)) = 2; total_w = 367 + 4 = 371
    img, _ = generate_frame("iphone-16-pro", 400, 800)
    scale = min(400 / 402, 800 / 874)
    fw = int(402 * scale)
    assert img.width > fw, "Image should be wider than fw to include button padding"


def test_generate_frame_screen_rect_sx_is_offset():
    """Returned sx should exceed the raw scaled screen.x (it includes btn_w)."""
    img, (sx, sy, sw, sh, _) = generate_frame("iphone-16-pro", 400, 800)
    scale = min(400 / 402, 800 / 874)
    raw_sx = int(14 * scale)   # spec screen.x = 14
    assert sx > raw_sx, "sx should be offset by btn_w"


# ── FINISH_PRESETS: border-color pixel round-trip ─────────────────────────────

@pytest.mark.parametrize("finish,expected_rgb", [
    ("black",            (0x1C, 0x1C, 0x1E)),
    ("matte-gray",       (0x48, 0x48, 0x4A)),
    ("natural-titanium", (0x8E, 0x8E, 0x93)),
])
def test_frame_border_pixel_matches_finish_color(finish, expected_rgb):
    """A pixel on the left frame wall carries the exact border hex from the preset.

    Geometry for iphone-16-pro at 400×800:
      scale = 800/874 ≈ 0.9153, btn_w = 2, sx ≈ 14
      x=5 is inside the frame body (btn_w=2) and left of the screen cutout (sx≈14).
      y=400 is mid-frame, far from any corner.
    """
    img, _ = generate_frame("iphone-16-pro", 400, 800, finish=finish)
    pixel = img.getpixel((5, 400))
    assert pixel[:3] == expected_rgb
    assert pixel[3] == 255  # fully opaque


def test_different_finishes_have_different_border_colors():
    """Each finish should produce a visually distinct frame color at the same pixel."""
    img_black, _ = generate_frame("iphone-16-pro", 400, 800, finish="black")
    img_ti, _    = generate_frame("iphone-16-pro", 400, 800, finish="natural-titanium")
    assert img_black.getpixel((5, 400))[:3] != img_ti.getpixel((5, 400))[:3]


# ── Invalid model ─────────────────────────────────────────────────────────────

def test_invalid_model_raises_value_error():
    with pytest.raises(ValueError, match="Unknown device frame model"):
        generate_frame("not-a-real-phone", 400, 800)


# ── Every available model ─────────────────────────────────────────────────────

@pytest.mark.parametrize("model", ALL_MODELS)
def test_every_model_produces_valid_rgba_output(model):
    """All TOML frame specs load and render without error."""
    img, (sx, sy, sw, sh, _) = generate_frame(model, 400, 800)
    assert img.mode == "RGBA"
    assert img.width > 0 and img.height > 0
    assert sw > 0 and sh > 0


# ── Screen cutout transparency ────────────────────────────────────────────────

def test_screen_cutout_center_is_transparent():
    """The midpoint of the screen area must be alpha=0 so screenshots show through."""
    img, (sx, sy, sw, sh, _) = generate_frame("iphone-16-pro", 400, 800)
    cx = sx + sw // 2
    cy = sy + sh // 2
    assert img.getpixel((cx, cy))[3] == 0


def test_ipad_screen_cutout_center_is_transparent():
    """iPad Pro frame (no Dynamic Island, rectangular cutout) should also be transparent."""
    img, (sx, sy, sw, sh, _) = generate_frame("ipad-pro-12-9", 400, 800)
    cx = sx + sw // 2
    cy = sy + sh // 2
    assert img.getpixel((cx, cy))[3] == 0


def test_pro_model_screen_has_positive_corner_radius():
    """Pro iPhones define a screen corner radius; it should survive scaling."""
    _, (_, _, _, _, screen_cr) = generate_frame("iphone-16-pro", 400, 800)
    assert screen_cr > 0


# ── render() integration ──────────────────────────────────────────────────────

def test_render_hero_without_screenshot_returns_rgb_at_canvas_size():
    """render() with no screenshot produces an RGB canvas at the configured size."""
    template = TemplateConfig()          # size=(1200, 630), layout="hero"
    image_config = ImageConfig(title="Hello World")   # screenshot=None → no file I/O
    result = render(template, image_config, Path("."))
    assert result.mode == "RGB"
    assert result.size == (1200, 630)


def test_render_hero_respects_custom_canvas_size():
    template = TemplateConfig()
    template.size = (800, 400)
    image_config = ImageConfig(title="Custom Size")
    result = render(template, image_config, Path("."))
    assert result.size == (800, 400)


@pytest.mark.parametrize("position", ["top", "bottom", "left", "right"])
def test_render_hero_all_text_positions_return_correct_canvas_size(position):
    """All four text-position variants must produce a canvas at exactly the configured size."""
    template = TemplateConfig()
    template.text.position = position
    image_config = ImageConfig(title="Layout test")
    result = render(template, image_config, Path("."))
    assert result.size == (1200, 630)


def test_render_unknown_layout_raises_value_error():
    template = TemplateConfig()
    template.layout = "grid"
    image_config = ImageConfig(title="Test")
    with pytest.raises(ValueError, match="Unknown layout"):
        render(template, image_config, Path("."))


def test_no_screenshot_yields_no_layout_info():
    """render_with_bounds with no screenshot path returns None for layout_info."""
    template = TemplateConfig()
    template.device_frame.enabled = True
    image_config = ImageConfig(title="Test")  # screenshot=None
    _, layout_info = render_with_bounds(template, image_config, Path("."))
    assert layout_info is None


def test_canvas_clamp_allows_device_past_ss_region(tmp_path):
    """layout_info.device_x stays within canvas even when offset pushes past ss_x2.

    Uses a "right" text-position layout where the screenshot region ends at ~60% of
    canvas width. With offset_x=3.0 the device would exceed ss_x2 under the old clamp;
    the canvas clamp ensures device_x stays within 0..width-device_w.
    """
    from PIL import Image as _PILImage
    ss_img = _PILImage.new("RGBA", (300, 600), (0, 128, 255, 255))
    ss_path = tmp_path / "screen.png"
    ss_img.save(ss_path)

    template = TemplateConfig()
    template.text.position = "right"   # screenshot on the left 60% of canvas
    template.screenshot.offset_x = 3.0
    template.screenshot.shadow = False
    template.device_frame.enabled = True
    image_config = ImageConfig(title="Clamp test", screenshot=str(ss_path))

    _, layout_info = render_with_bounds(template, image_config, tmp_path)

    assert layout_info is not None
    width, height = template.size
    device_x = layout_info["device_x"]
    device_w = layout_info["device_w"]
    ss_x2 = layout_info["ss_x2"]

    # Frame stays within canvas bounds
    assert device_x >= 0
    assert device_x + device_w <= width

    # Frame moved past the right edge of the screenshot region
    # (which the old ss-region clamp would have prevented)
    assert device_x > ss_x2 - device_w, (
        f"device_x={device_x} should exceed ss_x2-device_w={ss_x2 - device_w}"
    )


def test_device_can_go_off_left_edge(tmp_path):
    """Large negative offset_x places dev_x below zero (device clips off left edge).

    Uses "right" text-position layout: ss occupies left 60% of the 1200-wide canvas,
    so ss_x1=0, ss_x2=720, ss_w=720. offset_x=-3.0 produces a very negative dev_x
    that the new clamp allows down to -(content_w - _DEVICE_MIN_SLIVER).
    """
    from PIL import Image as _PILImage
    ss_img = _PILImage.new("RGBA", (300, 600), (0, 128, 255, 255))
    ss_path = tmp_path / "screen.png"
    ss_img.save(ss_path)

    template = TemplateConfig()
    template.text.position = "right"
    template.screenshot.offset_x = -3.0
    template.screenshot.shadow = False
    template.device_frame.enabled = True
    image_config = ImageConfig(title="Left edge test", screenshot=str(ss_path))

    _, layout_info = render_with_bounds(template, image_config, tmp_path)

    assert layout_info is not None
    device_x = layout_info["device_x"]
    device_w = layout_info["device_w"]

    assert device_x < 0, f"expected dev_x < 0, got {device_x}"
    assert device_x >= -(device_w - _DEVICE_MIN_SLIVER), (
        f"sliver violated: dev_x={device_x}, -(device_w - sliver)={-(device_w - _DEVICE_MIN_SLIVER)}"
    )


def test_device_can_go_off_right_edge(tmp_path):
    """Large positive offset_x places dev_x beyond width-content_w (clips off right edge).

    Uses "right" text-position layout: ss_w=720, canvas width=1200. offset_x=3.0
    produces a very large dev_x that the new clamp allows up to width - _DEVICE_MIN_SLIVER.
    """
    from PIL import Image as _PILImage
    ss_img = _PILImage.new("RGBA", (300, 600), (0, 128, 255, 255))
    ss_path = tmp_path / "screen.png"
    ss_img.save(ss_path)

    template = TemplateConfig()
    template.text.position = "right"
    template.screenshot.offset_x = 3.0
    template.screenshot.shadow = False
    template.device_frame.enabled = True
    image_config = ImageConfig(title="Right edge test", screenshot=str(ss_path))

    _, layout_info = render_with_bounds(template, image_config, tmp_path)

    assert layout_info is not None
    width = template.size[0]   # 1200
    device_x = layout_info["device_x"]
    device_w = layout_info["device_w"]

    assert device_x > width - device_w, (
        f"expected dev_x > width-device_w={width - device_w}, got {device_x}"
    )
    assert device_x <= width - _DEVICE_MIN_SLIVER, (
        f"sliver violated: dev_x={device_x}, width-sliver={width - _DEVICE_MIN_SLIVER}"
    )


def test_sliver_preserved_on_all_edges(tmp_path):
    """Extreme offsets in all four directions all respect the 40 px sliver and render without error."""
    from PIL import Image as _PILImage
    ss_img = _PILImage.new("RGBA", (300, 600), (0, 128, 255, 255))
    ss_path = tmp_path / "screen.png"
    ss_img.save(ss_path)

    for offset_x, offset_y in [(-4.0, 0.0), (4.0, 0.0), (0.0, -4.0), (0.0, 4.0)]:
        template = TemplateConfig()
        template.text.position = "right"
        template.screenshot.offset_x = offset_x
        template.screenshot.offset_y = offset_y
        template.screenshot.shadow = False
        template.device_frame.enabled = True
        image_config = ImageConfig(
            title=f"Sliver test ({offset_x},{offset_y})",
            screenshot=str(ss_path),
        )

        img, layout_info = render_with_bounds(template, image_config, tmp_path)

        assert img is not None
        assert layout_info is not None

        width, height = template.size
        dx = layout_info["device_x"]
        dy = layout_info["device_y"]
        dw = layout_info["device_w"]
        dh = layout_info["device_h"]

        assert dx >= -(dw - _DEVICE_MIN_SLIVER), f"left sliver violated at offset ({offset_x},{offset_y})"
        assert dx <= width  - _DEVICE_MIN_SLIVER, f"right sliver violated at offset ({offset_x},{offset_y})"
        assert dy >= -(dh - _DEVICE_MIN_SLIVER), f"top sliver violated at offset ({offset_x},{offset_y})"
        assert dy <= height - _DEVICE_MIN_SLIVER, f"bottom sliver violated at offset ({offset_x},{offset_y})"

from pathlib import Path

import pytest
from PIL import Image

from snaphaus.config import BackgroundConfig, ImageConfig, TemplateConfig
from snaphaus.renderer import _BEZEL_RGB, _hex_to_rgb, _DEVICE_MIN_SLIVER, _FRAMES_DIR, FINISH_PRESETS, create_background, generate_frame, render, render_with_bounds

# Discovered at import time so pytest.mark.parametrize can use it.
ALL_MODELS = sorted(p.stem for p in _FRAMES_DIR.glob("*.toml"))


def test_finish_presets_keys():
    assert set(FINISH_PRESETS.keys()) == {"black", "matte-gray", "natural-titanium"}


def test_finish_presets_have_required_colors():
    for name, preset in FINISH_PRESETS.items():
        assert "border" in preset, f"{name} missing 'border'"
        assert "highlight" in preset, f"{name} missing 'highlight'"
        assert "button" in preset, f"{name} missing 'button'"
        assert "shadow" in preset, f"{name} missing 'shadow'"


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


# ── Frame finish shading ──────────────────────────────────────────────────────

def _luma(rgb):
    return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]


@pytest.mark.parametrize("finish", sorted(FINISH_PRESETS))
def test_frame_band_mid_height_matches_finish_border_color(finish):
    """Mid-height on the metal band the vertical gradient sits on the preset border colour.

    Geometry for iphone-16-pro at 400×800:
      scale = 800/874 ≈ 0.9153, btn_w = 2, band_w = 8, edge_w = 1
      Band spans x∈[2,9]: x=2 silhouette edge, x=3 highlight, x=9 chamfer, x=4 plain band.
    """
    img, _ = generate_frame("iphone-16-pro", 400, 800, finish=finish)
    pixel = img.getpixel((4, 400))
    assert pixel[:3] == _hex_to_rgb(FINISH_PRESETS[finish]["border"])
    assert pixel[3] == 255


@pytest.mark.parametrize("finish", sorted(FINISH_PRESETS))
def test_frame_band_is_lit_from_above(finish):
    """The band gradient runs lighter at the top than at the bottom."""
    img, _ = generate_frame("iphone-16-pro", 400, 800, finish=finish)
    assert _luma(img.getpixel((4, 150))) > _luma(img.getpixel((4, 650)))


@pytest.mark.parametrize("finish", sorted(FINISH_PRESETS))
def test_frame_has_dark_glass_bezel_between_band_and_screen(finish):
    """Between the metal band (ends x=9) and the screen (starts sx≈14) sits the black bezel."""
    img, (sx, _, _, _, _) = generate_frame("iphone-16-pro", 400, 800, finish=finish)
    assert sx > 12
    assert img.getpixel((12, 400)) == (*_BEZEL_RGB, 255)


def test_frame_outer_edge_is_darker_than_band():
    """A dark silhouette line defines the outer edge against light backgrounds."""
    img, _ = generate_frame("iphone-16-pro", 400, 800, finish="natural-titanium")
    assert _luma(img.getpixel((2, 400))) < _luma(img.getpixel((4, 400)))


def test_side_button_is_shaded_across_its_width():
    """Left buttons are lit on the outer face and darker towards the band."""
    img, _ = generate_frame("iphone-16-pro", 400, 800, finish="natural-titanium")
    y = int(800 * 0.33)   # middle of the volume-up button
    assert img.getpixel((0, y))[3] == 255
    assert _luma(img.getpixel((0, y))) > _luma(img.getpixel((1, y)))


def test_different_finishes_have_different_border_colors():
    """Each finish should produce a visually distinct frame color at the same pixel."""
    img_black, _ = generate_frame("iphone-16-pro", 400, 800, finish="black")
    img_ti, _    = generate_frame("iphone-16-pro", 400, 800, finish="natural-titanium")
    assert img_black.getpixel((4, 400))[:3] != img_ti.getpixel((4, 400))[:3]


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


def test_render_hero_with_subtitle_returns_correct_canvas_size():
    """Subtitle must not change the canvas dimensions."""
    template = TemplateConfig()
    image_config = ImageConfig(title="Hello World", subtitle="A great app")
    result = render(template, image_config, Path("."))
    assert result.size == (1200, 630)


def test_render_hero_subtitle_produces_different_image_than_no_subtitle():
    """A non-empty subtitle must visually change the output."""
    template = TemplateConfig()
    without = render(template, ImageConfig(title="Hello"), Path("."))
    with_sub = render(template, ImageConfig(title="Hello", subtitle="Tagline"), Path("."))
    assert without.tobytes() != with_sub.tobytes()


@pytest.mark.parametrize("position", ["top", "bottom", "left", "right"])
def test_render_hero_subtitle_all_text_positions_return_correct_canvas_size(position):
    """Subtitle must not break layout for any text position."""
    template = TemplateConfig()
    template.text.position = position
    image_config = ImageConfig(title="Layout test", subtitle="Subtitle text")
    result = render(template, image_config, Path("."))
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
    """Device frame can extend past the screenshot region boundary with sliver preserved.

    Uses a "right" text-position layout where the screenshot region ends at ~60% of
    canvas width. With offset_x=3.0 the device exceeds ss_x2; the sliver clamp allows
    device_x up to width-40 (not just width-device_w) while keeping 40px on-canvas.
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

    # Frame can go partially off-canvas but the sliver must be preserved
    assert device_x >= -(device_w - _DEVICE_MIN_SLIVER), (
        f"left sliver violated: device_x={device_x}"
    )
    assert device_x <= width - _DEVICE_MIN_SLIVER, (
        f"right sliver violated: device_x={device_x}, width-sliver={width - _DEVICE_MIN_SLIVER}"
    )

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


# ── Image backgrounds ─────────────────────────────────────────────────────────

_STRIPES = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]


def _save_stripes(path: Path) -> None:
    """200x100 image of four 50px vertical stripes: red, green, blue, yellow."""
    img = Image.new("RGB", (200, 100))
    for i, color in enumerate(_STRIPES):
        img.paste(color, (i * 50, 0, (i + 1) * 50, 100))
    img.save(path)


def test_image_background_cover_fits_and_centre_crops(tmp_path):
    _save_stripes(tmp_path / "bg.png")
    bg = BackgroundConfig(type="image", path="bg.png")

    img = create_background((100, 100), bg, tmp_path)

    # Cover fit keeps the 2:1 aspect and crops the outer stripes; a stretch
    # would squeeze all four stripes into view instead.
    assert img.size == (100, 100)
    assert img.getpixel((25, 50)) == (0, 255, 0)
    assert img.getpixel((75, 50)) == (0, 0, 255)


def test_image_background_upscales_small_source(tmp_path):
    _save_stripes(tmp_path / "bg.png")
    bg = BackgroundConfig(type="image", path="bg.png")

    img = create_background((400, 400), bg, tmp_path)

    assert img.size == (400, 400)
    assert img.getpixel((100, 200)) == (0, 255, 0)
    assert img.getpixel((300, 200)) == (0, 0, 255)


def test_image_background_blur_softens_edges(tmp_path):
    src = Image.new("RGB", (100, 100), (0, 0, 0))
    src.paste((255, 255, 255), (50, 0, 100, 100))
    src.save(tmp_path / "bg.png")

    sharp = create_background((100, 100), BackgroundConfig(type="image", path="bg.png"), tmp_path)
    blurred = create_background((100, 100), BackgroundConfig(type="image", path="bg.png", blur=10), tmp_path)

    assert sharp.getpixel((48, 50)) == (0, 0, 0)
    assert 0 < blurred.getpixel((48, 50))[0] < 255


def test_image_background_dim_darkens(tmp_path):
    Image.new("RGB", (50, 50), (200, 100, 50)).save(tmp_path / "bg.png")
    bg = BackgroundConfig(type="image", path="bg.png", dim=0.5)

    img = create_background((50, 50), bg, tmp_path)

    assert img.getpixel((25, 25)) == pytest.approx((100, 50, 25), abs=1)


def test_image_background_transparent_pixels_render_black(tmp_path):
    Image.new("RGBA", (50, 50), (255, 255, 255, 0)).save(tmp_path / "bg.png")
    bg = BackgroundConfig(type="image", path="bg.png")

    img = create_background((50, 50), bg, tmp_path)

    assert img.mode == "RGB"
    assert img.getpixel((25, 25)) == (0, 0, 0)


def test_image_background_missing_file_raises(tmp_path):
    bg = BackgroundConfig(type="image", path="missing.png")

    with pytest.raises(FileNotFoundError):
        create_background((50, 50), bg, tmp_path)


def test_render_uses_image_background(tmp_path):
    Image.new("RGB", (64, 64), (10, 120, 200)).save(tmp_path / "bg.png")
    template = TemplateConfig()
    template.background = BackgroundConfig(type="image", path="bg.png")

    img = render(template, ImageConfig(title="Hi"), tmp_path)

    assert img.convert("RGB").getpixel((2, 2)) == (10, 120, 200)

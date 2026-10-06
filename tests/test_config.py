import pytest

from snaphaus.config import (
    BackgroundConfig,
    DeviceFrameConfig,
    DeviceFrameTransformConfig,
    FontConfig,
    ImageConfig,
    ScreenshotConfig,
    TemplateConfig,
    TextConfig,
    _make_background,
    _make_device_frame,
    _make_font,
    _make_screenshot,
    _make_text,
)


def test_device_frame_config_default_finish():
    cfg = DeviceFrameConfig()
    assert cfg.finish == "black"


def test_make_device_frame_reads_finish():
    cfg = _make_device_frame({"finish": "natural-titanium"})
    assert cfg.finish == "natural-titanium"


def test_make_device_frame_finish_defaults_to_black():
    cfg = _make_device_frame({})
    assert cfg.finish == "black"


def test_make_device_frame_reads_model_and_enabled():
    cfg = _make_device_frame({"enabled": True, "model": "iphone-16-pro", "finish": "matte-gray"})
    assert cfg.enabled is True
    assert cfg.model == "iphone-16-pro"
    assert cfg.finish == "matte-gray"


# ── DeviceFrameConfig: field presence and defaults ────────────────────────────

def test_device_frame_config_has_enabled_field():
    assert hasattr(DeviceFrameConfig(), "enabled")


def test_device_frame_config_has_model_field():
    assert hasattr(DeviceFrameConfig(), "model")


def test_device_frame_config_default_enabled_is_false():
    assert DeviceFrameConfig().enabled is False


def test_device_frame_config_default_model():
    assert DeviceFrameConfig().model == "iphone-15-pro"


# ── _make_device_frame: robustness ───────────────────────────────────────────

def test_make_device_frame_returns_device_frame_config_instance():
    assert isinstance(_make_device_frame({}), DeviceFrameConfig)


def test_make_device_frame_with_unknown_keys_does_not_raise():
    """Unknown keys must be silently ignored — forward-compat with future TOML additions."""
    cfg = _make_device_frame({"enabled": True, "unknown_field": "ignored", "another": 42})
    assert cfg.enabled is True   # known key still applied


# ── _make_background ──────────────────────────────────────────────────────────

def test_make_background_empty_dict_returns_defaults():
    cfg = _make_background({})
    assert cfg.type == "gradient"
    assert cfg.angle == 135


def test_make_background_reads_type():
    assert _make_background({"type": "solid"}).type == "solid"


def test_make_background_reads_colors():
    cfg = _make_background({"colors": ["#ff0000", "#0000ff"]})
    assert cfg.colors == ["#ff0000", "#0000ff"]


def test_make_background_reads_angle():
    assert _make_background({"angle": 90}).angle == 90


def test_make_background_reads_solid_color():
    assert _make_background({"color": "#abcdef"}).color == "#abcdef"


def test_make_background_unknown_keys_ignored():
    cfg = _make_background({"unknown": "value"})
    assert isinstance(cfg, BackgroundConfig)


def test_make_background_image_defaults():
    cfg = _make_background({})
    assert cfg.path == ""
    assert cfg.blur == 0
    assert cfg.dim == 0.0


def test_make_background_reads_image_fields():
    cfg = _make_background({"type": "image", "path": "bg.jpg", "blur": 12, "dim": 0.3})
    assert cfg.type == "image"
    assert cfg.path == "bg.jpg"
    assert cfg.blur == 12
    assert cfg.dim == 0.3


# ── _make_font ────────────────────────────────────────────────────────────────

def test_make_font_empty_dict_returns_defaults():
    cfg = _make_font({})
    assert cfg.size == 56
    assert cfg.color == "#ffffff"
    assert cfg.align == "center"


def test_make_font_reads_size():
    assert _make_font({"size": 72}).size == 72


def test_make_font_reads_color():
    assert _make_font({"color": "#ff0000"}).color == "#ff0000"


def test_make_font_reads_align():
    assert _make_font({"align": "left"}).align == "left"


def test_make_font_reads_path():
    assert _make_font({"path": "assets/fonts/Custom.ttf"}).path == "assets/fonts/Custom.ttf"


def test_make_font_unknown_keys_ignored():
    assert isinstance(_make_font({"nonexistent": True}), FontConfig)


# ── _make_screenshot ──────────────────────────────────────────────────────────

def test_make_screenshot_empty_dict_returns_defaults():
    cfg = _make_screenshot({})
    assert cfg.enabled is True
    assert cfg.scale == pytest.approx(0.70)
    assert cfg.shadow is True


def test_make_screenshot_reads_enabled():
    assert _make_screenshot({"enabled": False}).enabled is False


def test_make_screenshot_reads_scale():
    assert _make_screenshot({"scale": 0.85}).scale == pytest.approx(0.85)


def test_make_screenshot_reads_shadow_blur():
    assert _make_screenshot({"shadow_blur": 20}).shadow_blur == 20


def test_make_screenshot_reads_rounded_corners():
    assert _make_screenshot({"rounded_corners": 24}).rounded_corners == 24


def test_make_screenshot_unknown_keys_ignored():
    assert isinstance(_make_screenshot({"nonexistent": True}), ScreenshotConfig)


# ── _make_text ────────────────────────────────────────────────────────────────

def test_make_text_empty_dict_returns_default_position():
    assert _make_text({}).position == "top"


@pytest.mark.parametrize("position", ["top", "bottom", "left", "right"])
def test_make_text_reads_position(position):
    assert _make_text({"position": position}).position == position


def test_make_text_unknown_keys_ignored():
    assert isinstance(_make_text({"irrelevant": "data"}), TextConfig)


# ── TemplateConfig defaults ───────────────────────────────────────────────────

def test_template_config_default_size():
    assert TemplateConfig().size == (1200, 630)


def test_template_config_default_layout():
    assert TemplateConfig().layout == "hero"


def test_template_config_default_padding():
    assert TemplateConfig().padding == 60


def test_template_config_device_frame_field_is_device_frame_config():
    assert isinstance(TemplateConfig().device_frame, DeviceFrameConfig)


def test_template_config_screenshot_field_is_screenshot_config():
    assert isinstance(TemplateConfig().screenshot, ScreenshotConfig)


# ── ImageConfig defaults ──────────────────────────────────────────────────────

def test_image_config_default_screenshot_is_none():
    assert ImageConfig().screenshot is None


def test_image_config_default_title_is_empty_string():
    assert ImageConfig().title == ""


def test_image_config_default_output_is_empty_string():
    assert ImageConfig().output == ""


def test_image_config_default_subtitle_is_empty_string():
    assert ImageConfig().subtitle == ""


def test_image_config_accepts_subtitle():
    cfg = ImageConfig(title="My App", subtitle="The best app")
    assert cfg.subtitle == "The best app"


def test_image_config_accepts_all_fields():
    cfg = ImageConfig(title="My App", subtitle="Tagline", screenshot="screens/main.png", output="out.png")
    assert cfg.title == "My App"
    assert cfg.subtitle == "Tagline"
    assert cfg.screenshot == "screens/main.png"
    assert cfg.output == "out.png"


def test_device_frame_transform_config_defaults():
    cfg = DeviceFrameTransformConfig()
    assert cfg.mode == "none"
    assert cfg.tilt_angle == -15.0
    assert cfg.iso_variant == "left"
    assert cfg.float_preset == "left-lean"


def test_device_frame_config_has_transform_field():
    cfg = DeviceFrameConfig()
    assert hasattr(cfg, "transform")
    assert cfg.transform.mode == "none"


def test_make_device_frame_parses_nested_transform():
    cfg = _make_device_frame({"transform": {"mode": "tilt", "tilt_angle": 20.0}})
    assert cfg.transform.mode == "tilt"
    assert cfg.transform.tilt_angle == 20.0


def test_make_device_frame_transform_defaults_when_absent():
    cfg = _make_device_frame({})
    assert cfg.transform.mode == "none"


def test_make_device_frame_parses_iso_variant():
    cfg = _make_device_frame({"transform": {"mode": "iso", "iso_variant": "right"}})
    assert cfg.transform.iso_variant == "right"


def test_make_device_frame_parses_float_preset():
    cfg = _make_device_frame({"transform": {"mode": "float", "float_preset": "right-lean"}})
    assert cfg.transform.float_preset == "right-lean"

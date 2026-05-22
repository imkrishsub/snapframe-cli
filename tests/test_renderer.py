from snapframe.renderer import FINISH_PRESETS, generate_frame


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

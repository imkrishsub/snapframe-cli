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


def test_generate_frame_iphone_has_dynamic_island_pixels():
    """The DI pill area should be near-black (drawn on top of the transparent screen cutout)."""
    img, _ = generate_frame("iphone-16-pro", 402, 874)
    # scale ≈ 1.0, btn_w = max(2, int(3*1.0)) = 3
    # DI spec: x=138, w=126 → centre_x = (138 + 3) + 63 = 204; y=14, h=37 → centre_y = 14 + 18 = 32
    pixel = img.getpixel((204, 32))
    assert pixel[3] > 0, "Dynamic Island area should be opaque"
    assert pixel[0] < 20 and pixel[1] < 20 and pixel[2] < 20, "Should be near-black"


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

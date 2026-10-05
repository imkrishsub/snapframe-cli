from __future__ import annotations

import math
import tomllib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .config import DeviceFrameConfig, DeviceFrameTransformConfig, FontConfig, ImageConfig, ScreenshotConfig, TemplateConfig

_FRAMES_DIR = Path(__file__).parent / "frames"

# Metal band colours per finish: ``highlight`` (lit top edge / chamfers),
# ``border`` (band mid-tone), ``shadow`` (band bottom / outer edge), ``button``.
FINISH_PRESETS: dict[str, dict[str, str]] = {
    "black":            {"border": "#2e2e30", "highlight": "#5c5c60", "shadow": "#161618", "button": "#2a2a2c"},
    "matte-gray":       {"border": "#6c6c70", "highlight": "#a1a1a6", "shadow": "#45454a", "button": "#5f5f64"},
    "natural-titanium": {"border": "#b5afa5", "highlight": "#e0dbd2", "shadow": "#857f75", "button": "#a59f95"},
}

_BEZEL_RGB = (8, 8, 10)     # black glass between the metal band and the screen
_BAND_FRACTION = 0.3        # share of the spec border_width that is metal band; the rest is bezel

_DEVICE_MIN_SLIVER = 40  # px — minimum on-canvas sliver when device is dragged off an edge


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def _interpolate_color(
    a: tuple[int, int, int], b: tuple[int, int, int], t: float
) -> tuple[int, int, int]:
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _interpolate_colors(rgb_colors: list[tuple[int, int, int]], t: float) -> tuple[int, int, int]:
    """Multi-stop gradient interpolation. t is in [0, 1]."""
    if len(rgb_colors) == 1:
        return rgb_colors[0]

    num_segments = len(rgb_colors) - 1
    scaled = t * num_segments
    segment = min(int(scaled), num_segments - 1)
    local_t = scaled - segment

    return _interpolate_color(rgb_colors[segment], rgb_colors[segment + 1], local_t)


_SYSTEM_FONTS = [
    # macOS
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
    # Linux
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def _load_font(font_config: FontConfig, project_root: Path) -> ImageFont.ImageFont:
    font_path = project_root / font_config.path
    try:
        font = ImageFont.truetype(str(font_path), font_config.size)
        try:
            axes = font.get_variation_axes()
            weight_axes = [a for a in axes if a["name"] in (b"Weight", b"wght")]
            if weight_axes:
                ax = weight_axes[0]
                font.set_variation_by_axes([min(ax["maximum"], max(ax["minimum"], 700))])
        except OSError:
            pass
        return font
    except (OSError, IOError):
        print(f"Warning: font not found at '{font_path}', falling back to system font.")

    for system_font in _SYSTEM_FONTS:
        try:
            return ImageFont.truetype(system_font, font_config.size)
        except (OSError, IOError):
            continue

    print("Warning: no font found, falling back to PIL default (very small).")
    try:
        return ImageFont.load_default(size=font_config.size)
    except TypeError:
        return ImageFont.load_default()


_UNICODE_REPLACEMENTS = {
    "\u2014": " - ",   # em dash —
    "\u2013": "-",     # en dash –
    "\u2018": "'",     # left single quote '
    "\u2019": "'",     # right single quote '
    "\u201c": '"',     # left double quote "
    "\u201d": '"',     # right double quote "
    "\u2026": "...",   # ellipsis …
    "\u00a0": " ",     # non-breaking space
    "\u2022": "*",     # bullet •
}


def _sanitize_text(text: str) -> str:
    for char, replacement in _UNICODE_REPLACEMENTS.items():
        text = text.replace(char, replacement)
    return text


def _wrap_text(text: str, font: ImageFont.ImageFont, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
    words = text.split()
    lines = []
    current = ""

    for word in words:
        candidate = f"{current} {word}".strip() if current else word
        bbox = draw.textbbox((0, 0), candidate, font=font)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines if lines else [text]


def create_gradient(size: tuple[int, int], colors: list[str], angle: int = 135) -> Image.Image:
    width, height = size
    strip_width = 1024

    rgb_colors = [_hex_to_rgb(c) for c in colors]

    # Build a 1×strip_width gradient strip
    strip_data = []
    for i in range(strip_width):
        t = i / (strip_width - 1)
        strip_data.append(_interpolate_colors(rgb_colors, t))

    strip = Image.new("RGB", (strip_width, 1))
    strip.putdata(strip_data)

    # CSS angle convention: 0° = bottom to top, 90° = left to right
    angle_rad = math.radians(angle)
    dx = math.sin(angle_rad)
    dy = -math.cos(angle_rad)

    gradient_length = abs(width * dx) + abs(height * dy)
    cx, cy = width / 2, height / 2
    scale = (strip_width - 1) / gradient_length

    a = dx * scale
    b = dy * scale
    c = (-cx * dx - cy * dy + gradient_length / 2) * scale

    result = strip.transform(
        (width, height),
        Image.AFFINE,
        (a, b, c, 0, 0, 0),
        resample=Image.BILINEAR,
    )

    return result


def create_background(size: tuple[int, int], bg_config) -> Image.Image:
    if bg_config.type == "gradient":
        return create_gradient(size, bg_config.colors, bg_config.angle)
    else:
        rgb = _hex_to_rgb(bg_config.color)
        return Image.new("RGB", size, rgb)


def apply_rounded_corners(img: Image.Image, radius: int) -> Image.Image:
    img = img.convert("RGBA")
    mask = Image.new("L", img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), (img.width - 1, img.height - 1)], radius=radius, fill=255)
    img.putalpha(mask)
    return img


def add_shadow(
    img: Image.Image,
    blur: int,
    opacity: float,
    offset: tuple[int, int] = (0, 15),
) -> Image.Image:
    img = img.convert("RGBA")
    pad = blur * 2
    result_w = img.width + 2 * pad
    result_h = img.height + 2 * pad

    # Create shadow layer
    shadow_layer = Image.new("RGBA", (result_w, result_h), (0, 0, 0, 0))

    # Use the alpha channel of original to build shadow shape
    r, g, b, alpha = img.split()
    shadow_alpha = alpha.point(lambda p: int(p * opacity))
    shadow_rgb = Image.new("RGB", img.size, (0, 0, 0))
    shadow_img = Image.merge("RGBA", (shadow_rgb.split()[0], shadow_rgb.split()[1], shadow_rgb.split()[2], shadow_alpha))

    shadow_x = pad + offset[0]
    shadow_y = pad + offset[1]
    shadow_layer.paste(shadow_img, (shadow_x, shadow_y), shadow_img)

    # Blur the shadow
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(blur))

    # Composite original on top of shadow
    result = Image.new("RGBA", (result_w, result_h), (0, 0, 0, 0))
    result.paste(shadow_layer, (0, 0), shadow_layer)
    result.paste(img, (pad, pad), img)

    return result


def _apply_tilt(img: Image.Image, angle: float) -> Image.Image:
    return img.rotate(-angle, expand=True, resample=Image.BICUBIC)


_ISO_SIN = math.sin(math.radians(30))  # 0.5
_ISO_COS = math.cos(math.radians(30))  # 0.866
_ISO_TAN = math.tan(math.radians(30))  # 0.577


def _iso_scale(w: int, h: int) -> float:
    """Uniform scale that keeps the projected device at its pre-transform height."""
    return h / (h + w * _ISO_SIN)


def _apply_iso(img: Image.Image, variant: str) -> Image.Image:
    """Project the device onto a vertical face of an isometric cube.

    Vertical edges stay vertical; horizontal edges run along the 30° isometric
    axis and are foreshortened to cos 30°.  The result is scaled uniformly by
    k = _iso_scale(w, h) so it fits the same height as the unprojected device:

        'left'  → left face, right side lower:  x' = k·x·cos30, y' = k·(y + x·sin30)
        'right' → right face, left side lower:  x' = k·x·cos30, y' = k·(y + (w − x)·sin30)

    Pillow AFFINE takes the inverse (output → source) mapping.
    """
    w, h = img.size
    k = _iso_scale(w, h)
    out_size = (round(k * w * _ISO_COS), h)
    if variant == "left":
        coeffs = (1 / (k * _ISO_COS), 0, 0, -_ISO_TAN / k, 1 / k, 0)
    else:
        coeffs = (1 / (k * _ISO_COS), 0, 0, _ISO_TAN / k, 1 / k, -w * _ISO_SIN)
    return img.transform(out_size, Image.AFFINE, coeffs, resample=Image.BICUBIC)


# Float: the device is rotated about its vertical centre axis and viewed through
# a pinhole camera.  The near edge keeps the device's full height; the far edge
# shrinks and the width foreshortens, as a real turned device would.
_FLOAT_ANGLE_DEG = 30.0
_FLOAT_CAMERA_DISTANCE = 2.0  # multiples of device height


def _float_corners(w: int, h: int, preset: str) -> list[tuple[float, float]]:
    """Return the projected device corners (TL, TR, BR, BL) for a float preset.

    'left-lean'  → right edge towards viewer, left side recedes.
    'right-lean' → mirror of left-lean.
    Unknown presets fall back to 'left-lean'.

    Coordinates are normalised so the near edge spans y ∈ [0, h] and min x = 0.
    """
    sin_a = math.sin(math.radians(_FLOAT_ANGLE_DEG))
    cos_a = math.cos(math.radians(_FLOAT_ANGLE_DEG))
    d = _FLOAT_CAMERA_DISTANCE * h
    # Depth z grows away from the camera; the left half recedes for left-lean.
    near_k = d / (d - w / 2 * sin_a)
    pts = []
    for x, y in [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]:
        k = d / (d - x * sin_a) / near_k
        pts.append((x * cos_a * k, y * k + h / 2))
    min_x = min(px for px, _ in pts)
    pts = [(px - min_x, py) for px, py in pts]
    if preset == "right-lean":
        out_w = max(px for px, _ in pts)
        tl, tr, br, bl = [(out_w - px, py) for px, py in pts]
        pts = [tr, tl, bl, br]
    return pts


def _solve_perspective(
    dst: list[tuple[float, float]], src: list[tuple[float, float]]
) -> tuple[float, ...]:
    """Return Pillow PERSPECTIVE coefficients mapping each dst point to its src point.

    Pillow evaluates the inverse mapping per output pixel:
        x_src = (a·x + b·y + c) / (g·x + h·y + 1)
        y_src = (d·x + e·y + f) / (g·x + h·y + 1)
    """
    rows = []
    for (x, y), (u, v) in zip(dst, src):
        rows.append([x, y, 1, 0, 0, 0, -x * u, -y * u, u])
        rows.append([0, 0, 0, x, y, 1, -x * v, -y * v, v])
    # Gauss-Jordan elimination with partial pivoting on the 8×9 augmented matrix
    n = 8
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(rows[r][col]))
        rows[col], rows[pivot] = rows[pivot], rows[col]
        pv = rows[col][col]
        rows[col] = [val / pv for val in rows[col]]
        for r in range(n):
            if r != col and rows[r][col]:
                factor = rows[r][col]
                rows[r] = [rv - factor * cv for rv, cv in zip(rows[r], rows[col])]
    return tuple(rows[r][n] for r in range(n))


def _apply_float(img: Image.Image, preset: str) -> Image.Image:
    """Apply camera perspective for a floating-device look (see _float_corners)."""
    rgba = img if img.mode == "RGBA" else img.convert("RGBA")
    w, h = rgba.size
    corners = _float_corners(w, h, preset)
    out_w = round(max(x for x, _ in corners))
    coeffs = _solve_perspective(corners, [(0, 0), (w, 0), (w, h), (0, h)])
    return rgba.transform((out_w, h), Image.PERSPECTIVE, coeffs, resample=Image.BICUBIC)


def apply_transform(img: Image.Image, transform: DeviceFrameTransformConfig) -> Image.Image:
    if transform.mode == "tilt":
        return _apply_tilt(img, transform.tilt_angle)
    if transform.mode == "iso":
        return _apply_iso(img, transform.iso_variant)
    if transform.mode == "float":
        return _apply_float(img, transform.float_preset)
    return img


def projected_corners(
    transform: DeviceFrameTransformConfig,
    pre_w: int,
    pre_h: int,
    post_w: int,
    post_h: int,
    dev_x: int,
    dev_y: int,
) -> list[tuple[float, float]]:
    """Return the 4 real device corners in canvas space (TL, TR, BR, BL)."""
    if transform.mode == "tilt":
        # _apply_tilt calls img.rotate(-tilt_angle), which is PIL CCW rotation
        # by -tilt_angle.  Negate here so the corner formula matches the actual
        # pixel positions in the output image.
        a = math.radians(-transform.tilt_angle)
        cx_in, cy_in = pre_w / 2, pre_h / 2
        cx_out, cy_out = post_w / 2, post_h / 2
        result = []
        for x, y in [(0, 0), (pre_w, 0), (pre_w, pre_h), (0, pre_h)]:
            dx, dy = x - cx_in, y - cy_in
            rx = cx_out + math.cos(a) * dx + math.sin(a) * dy
            ry = cy_out - math.sin(a) * dx + math.cos(a) * dy
            result.append((dev_x + rx, dev_y + ry))
        return result

    if transform.mode == "iso":
        k = _iso_scale(pre_w, pre_h)
        dx = k * pre_w * _ISO_COS
        dy = k * pre_w * _ISO_SIN
        edge = k * pre_h
        if transform.iso_variant == "left":
            raw = [
                (0,   0),
                (dx,  dy),
                (dx,  dy + edge),
                (0,   edge),
            ]
        else:  # right
            raw = [
                (0,   dy),
                (dx,  0),
                (dx,  edge),
                (0,   dy + edge),
            ]
        return [(dev_x + cx, dev_y + cy) for cx, cy in raw]

    if transform.mode == "float":
        raw = _float_corners(pre_w, pre_h, transform.float_preset)
        return [(dev_x + cx, dev_y + cy) for cx, cy in raw]

    if transform.mode == "none":
        return [
            (float(dev_x),           float(dev_y)),
            (float(dev_x + post_w),  float(dev_y)),
            (float(dev_x + post_w),  float(dev_y + post_h)),
            (float(dev_x),           float(dev_y + post_h)),
        ]
    raise ValueError(
        f"Unknown transform mode {transform.mode!r}. "
        f"Expected one of: 'none', 'tilt', 'iso', 'float'."
    )


def _load_frame_spec(model: str) -> dict:
    sidecar = _FRAMES_DIR / f"{model}.toml"
    if not sidecar.exists():
        raise ValueError(f"Unknown device frame model '{model}'. Available: {', '.join(p.stem for p in _FRAMES_DIR.glob('*.toml'))}")
    with open(sidecar, "rb") as f:
        return tomllib.load(f)


def _linear_fill(
    size: tuple[int, int], rgb_colors: list[tuple[int, int, int]], horizontal: bool = False
) -> Image.Image:
    """Return an RGBA image filled with a multi-stop linear gradient (top→bottom or left→right)."""
    steps = 256
    strip = Image.new("RGB", (steps, 1) if horizontal else (1, steps))
    strip.putdata([_interpolate_colors(rgb_colors, i / (steps - 1)) for i in range(steps)])
    return strip.resize(size, Image.BILINEAR).convert("RGBA")


def generate_frame(
    model: str,
    target_width: int,
    target_height: int,
    finish: str = "black",
) -> tuple[Image.Image, tuple[int, int, int, int, int]]:
    """Render a scaled device-frame image for the given model and finish.

    Returns ``(frame_image, (sx, sy, sw, sh, screen_cr))`` where ``sx`` is
    offset from the raw spec by ``btn_w`` to account for button protrusion on
    the left side.
    """
    spec = _load_frame_spec(model)
    ref_w = spec["frame"]["width"]
    ref_h = spec["frame"]["height"]

    scale = min(target_width / ref_w, target_height / ref_h)
    fw = int(ref_w * scale)
    fh = int(ref_h * scale)

    corner_r = int(spec["frame"]["corner_radius"] * scale)
    btn_w = max(2, int(3 * scale))
    band_w = max(2, round(spec["frame"]["border_width"] * _BAND_FRACTION * scale))
    edge_w = max(1, round(0.75 * scale))

    preset = FINISH_PRESETS.get(finish, FINISH_PRESETS["black"])
    border_rgb = _hex_to_rgb(preset["border"])
    highlight_rgb = _hex_to_rgb(preset["highlight"])
    shadow_rgb = _hex_to_rgb(preset["shadow"])
    button_rgb = _hex_to_rgb(preset["button"])

    sx = int(spec["screen"]["x"] * scale) + btn_w
    sy = int(spec["screen"]["y"] * scale)
    sw = int(spec["screen"]["width"] * scale)
    sh = int(spec["screen"]["height"] * scale)
    screen_cr = int(spec["screen"].get("corner_radius", 0) * scale)

    total_w = fw + 2 * btn_w
    frame = Image.new("RGBA", (total_w, fh), (0, 0, 0, 0))

    # Side buttons: drawn first so the body overlaps their inner end. Shaded
    # across their width, lit on the outer face and darker where they meet the band.
    buttons = [
        ("left",  0.21, 0.06),   # action
        ("left",  0.29, 0.08),   # volume up
        ("left",  0.39, 0.11),   # volume down
        ("right", 0.24, 0.11),   # power
    ]
    btn_r = max(1, btn_w // 2)
    btn_depth = btn_w + max(1, btn_w // 2)
    btn_stops = [highlight_rgb, button_rgb, shadow_rgb]
    for side, y_frac, h_frac in buttons:
        by = int(fh * y_frac)
        bh = max(2, int(fh * h_frac))
        stops = btn_stops if side == "left" else btn_stops[::-1]
        bx = 0 if side == "left" else total_w - btn_depth
        mask = Image.new("L", (btn_depth, bh), 0)
        ImageDraw.Draw(mask).rounded_rectangle([(0, 0), (btn_depth - 1, bh - 1)], radius=btn_r, fill=255)
        frame.paste(_linear_fill((btn_depth, bh), stops, horizontal=True), (bx, by), mask)

    # Metal band: vertical gradient, lit from above
    body_box = [(btn_w, 0), (btn_w + fw - 1, fh - 1)]
    body_mask = Image.new("L", frame.size, 0)
    ImageDraw.Draw(body_mask).rounded_rectangle(body_box, radius=corner_r, fill=255)
    band_top = _interpolate_color(highlight_rgb, border_rgb, 0.5)
    frame.paste(_linear_fill(frame.size, [band_top, border_rgb, border_rgb, shadow_rgb]), (0, 0), body_mask)

    # Edge lighting: dark silhouette line, machined highlight just inside it,
    # and a chamfer highlight where the band meets the glass.
    def inset(n: int) -> list[tuple[int, int]]:
        return [(body_box[0][0] + n, n), (body_box[1][0] - n, fh - 1 - n)]

    edges = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    edge_draw = ImageDraw.Draw(edges)
    edge_draw.rounded_rectangle(inset(0), radius=corner_r, outline=(*shadow_rgb, 220), width=edge_w)
    edge_draw.rounded_rectangle(
        inset(edge_w), radius=max(0, corner_r - edge_w), outline=(*highlight_rgb, 150), width=edge_w
    )
    edge_draw.rounded_rectangle(
        inset(band_w - edge_w), radius=max(0, corner_r - band_w + edge_w), outline=(*highlight_rgb, 110), width=edge_w
    )
    frame.alpha_composite(edges)

    # Glass bezel ring between the band and the screen
    draw = ImageDraw.Draw(frame)
    draw.rounded_rectangle(inset(band_w), radius=max(0, corner_r - band_w), fill=(*_BEZEL_RGB, 255))

    # Screen cutout
    if screen_cr > 0:
        draw.rounded_rectangle(
            [(sx, sy), (sx + sw - 1, sy + sh - 1)],
            radius=screen_cr,
            fill=(0, 0, 0, 0),
        )
    else:
        draw.rectangle([(sx, sy), (sx + sw - 1, sy + sh - 1)], fill=(0, 0, 0, 0))

    return frame, (sx, sy, sw, sh, screen_cr)


def apply_device_frame(
    screenshot: Image.Image,
    frame_config: DeviceFrameConfig,
    available_width: int,
    available_height: int,
    ss_config: ScreenshotConfig,
) -> tuple[Image.Image, tuple[int, int]]:
    """Composite screenshot inside a device frame and return (composite, content_size).

    The composite image has the screenshot filling the frame's screen area, with the
    frame border drawn on top. Shadow (if enabled) is applied to the whole composite.
    """
    frame_img, (sx, sy, sw, sh, screen_cr) = generate_frame(frame_config.model, available_width, available_height, frame_config.finish)
    fw, fh = frame_img.size

    # Resize screenshot to fill the screen area exactly, then clip to screen shape
    ss_resized = screenshot.resize((sw, sh), Image.LANCZOS)
    if screen_cr > 0:
        ss_resized = apply_rounded_corners(ss_resized, screen_cr)

    # Build composite: transparent canvas → paste screenshot at screen position → paste frame on top
    composite = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))
    composite.paste(ss_resized, (sx, sy), ss_resized)
    composite.paste(frame_img, (0, 0), frame_img)

    content_size = (fw, fh)
    return composite, content_size


def _load_screenshot(
    path: str,
    config: ScreenshotConfig,
    available_width: int,
    available_height: int,
    project_root: Path,
    device_frame: DeviceFrameConfig | None = None,
    apply_shadow: bool = True,
) -> tuple[Image.Image, tuple[int, int]]:
    img = Image.open(project_root / path).convert("RGBA")

    if device_frame and device_frame.enabled:
        # Scale both dimensions uniformly so that resize drag always produces
        # a visible change (previously only max_w was scaled, so height-
        # constrained devices like phones were unaffected by scale changes).
        max_w = int(available_width * config.scale)
        max_h = int(available_height * config.scale)
        # apply_device_frame never adds shadow; caller applies it after any transforms
        composite, content_size = apply_device_frame(img, device_frame, max_w, max_h, config)
        if apply_shadow and config.shadow:
            composite = add_shadow(composite, config.shadow_blur, config.shadow_opacity)
        return composite, content_size

    # No device frame — original path
    target_w = int(available_width * config.scale)
    aspect = img.height / img.width
    target_h = int(target_w * aspect)

    max_h = int(available_height * config.scale)
    if target_h > max_h:
        target_h = max_h
        target_w = int(target_h / aspect)

    img = img.resize((target_w, target_h), Image.LANCZOS)
    content_size = (target_w, target_h)

    if config.rounded_corners > 0:
        img = apply_rounded_corners(img, config.rounded_corners)

    if apply_shadow and config.shadow:
        img = add_shadow(img, config.shadow_blur, config.shadow_opacity)

    return img, content_size


def render_hero(
    template: TemplateConfig,
    image_config: ImageConfig,
    project_root: Path,
) -> Image.Image:
    width, height = template.size
    pad = template.padding
    text_pos = template.text.position
    has_screenshot = (
        template.screenshot.enabled
        and image_config.screenshot is not None
    )

    bg = create_background(template.size, template.background)

    # We need a draw object to measure text
    dummy_img = Image.new("RGB", (1, 1))
    draw = ImageDraw.Draw(dummy_img)
    font = _load_font(template.font, project_root)
    font_color = _hex_to_rgb(template.font.color)

    # Determine text area width for wrapping
    if text_pos in ("left", "right") and has_screenshot:
        text_area_w = int(width * 0.40) - 2 * pad
    else:
        text_area_w = width - 2 * pad

    lines = _wrap_text(_sanitize_text(image_config.title), font, text_area_w, draw)

    # Measure title lines
    line_metrics = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        lh = bbox[3] - bbox[1]
        line_metrics.append((lw, lh))

    line_h = max(lh for _, lh in line_metrics) if line_metrics else 0
    line_spacing = int(line_h * 0.3)
    title_block_h = len(lines) * line_h + max(0, len(lines) - 1) * line_spacing
    total_text_h = title_block_h

    # Subtitle: 60% font size, same color at 75% opacity, half-line-height gap
    subtitle_font = None
    subtitle_lines: list[str] = []
    subtitle_metrics: list[tuple[int, int]] = []
    subtitle_gap = 0
    subtitle_block_h = 0

    if image_config.subtitle:
        sub_fc = FontConfig(
            path=template.font.path,
            size=int(template.font.size * 0.6),
            color=template.font.color,
            align=template.font.align,
        )
        subtitle_font = _load_font(sub_fc, project_root)
        subtitle_lines = _wrap_text(_sanitize_text(image_config.subtitle), subtitle_font, text_area_w, draw)
        for sub_line in subtitle_lines:
            bbox = draw.textbbox((0, 0), sub_line, font=subtitle_font)
            subtitle_metrics.append((bbox[2] - bbox[0], bbox[3] - bbox[1]))
        sub_line_h = max(lh for _, lh in subtitle_metrics) if subtitle_metrics else 0
        sub_line_spacing = int(sub_line_h * 0.3)
        subtitle_gap = line_h // 2
        subtitle_block_h = len(subtitle_lines) * sub_line_h + max(0, len(subtitle_lines) - 1) * sub_line_spacing
        total_text_h += subtitle_gap + subtitle_block_h

    # Layout regions
    if text_pos in ("top", "bottom"):
        # Ensure the text band is at least 15% of the canvas height so that on
        # tall portrait canvases a single short line doesn't produce a tiny sliver.
        min_text_h = int(height * 0.15)
        text_block_h = max(total_text_h + 2 * pad, min_text_h)
        ss_block_h = height - text_block_h

        if text_pos == "top":
            tx1, ty1, tx2, ty2 = 0, 0, width, text_block_h
            ss_x1, ss_y1, ss_x2, ss_y2 = 0, text_block_h, width, height
        else:
            ss_x1, ss_y1, ss_x2, ss_y2 = 0, 0, width, ss_block_h
            tx1, ty1, tx2, ty2 = 0, ss_block_h, width, height

        ss_w = ss_x2 - ss_x1
        ss_h = ss_y2 - ss_y1

    elif text_pos in ("left", "right"):
        split = int(width * 0.40)
        if text_pos == "left":
            tx1, ty1, tx2, ty2 = 0, 0, split, height
            ss_x1, ss_y1, ss_x2, ss_y2 = split, 0, width, height
        else:
            ss_x1, ss_y1, ss_x2, ss_y2 = 0, 0, width - split, height
            tx1, ty1, tx2, ty2 = width - split, 0, width, height

        ss_w = ss_x2 - ss_x1
        ss_h = ss_y2 - ss_y1

    else:
        tx1, ty1, tx2, ty2 = 0, 0, width, height
        ss_x1, ss_y1, ss_x2, ss_y2 = 0, 0, 0, 0
        ss_w, ss_h = 0, 0

    # Draw on background
    result = bg.convert("RGBA")
    draw = ImageDraw.Draw(result)

    # Vertically center text block (title + optional subtitle) within text region
    text_region_w = tx2 - tx1
    text_region_h = ty2 - ty1
    text_start_y = ty1 + (text_region_h - total_text_h) // 2

    for i, (line, (lw, lh)) in enumerate(zip(lines, line_metrics)):
        y = text_start_y + i * (lh + line_spacing)

        align = template.font.align
        if align == "center":
            x = tx1 + (text_region_w - lw) // 2
        elif align == "right":
            x = tx2 - pad - lw
        else:
            x = tx1 + pad

        draw.text((x, y), line, font=font, fill=font_color)

    # Draw subtitle if present
    if subtitle_font and subtitle_lines:
        r, g, b = font_color
        subtitle_color = (r, g, b, int(255 * 0.75))
        sub_line_h = max(lh for _, lh in subtitle_metrics)
        sub_line_spacing = int(sub_line_h * 0.3)
        sub_start_y = text_start_y + title_block_h + subtitle_gap
        align = template.font.align
        for j, (sub_line, (slw, slh)) in enumerate(zip(subtitle_lines, subtitle_metrics)):
            sy = sub_start_y + j * (slh + sub_line_spacing)
            if align == "center":
                sx = tx1 + (text_region_w - slw) // 2
            elif align == "right":
                sx = tx2 - pad - slw
            else:
                sx = tx1 + pad
            draw.text((sx, sy), sub_line, font=subtitle_font, fill=subtitle_color)

    # Draw screenshot
    layout_info = None

    if has_screenshot:
        # For projected transforms (tilt/iso/float), load shadow-free so we can apply the
        # transform first, then add shadow afterward.  This keeps projected_corners and the
        # dev_x/dev_y centring in shadow-free coordinate space throughout.
        is_projected = (
            template.device_frame
            and template.device_frame.enabled
            and template.device_frame.transform.mode != "none"
        )
        ss_img, (content_w, content_h) = _load_screenshot(
            image_config.screenshot,
            template.screenshot,
            ss_w,
            ss_h,
            project_root,
            device_frame=template.device_frame,
            apply_shadow=not is_projected,
        )

        # Save pre-transform, shadow-free frame dimensions for layout_info
        content_w_visual = content_w
        content_h_visual = content_h

        if is_projected:
            ss_img = apply_transform(ss_img, template.device_frame.transform)
            # content_w/h are now shadow-free post-transform dimensions — used for centering
            # and passed to projected_corners as post_w/post_h
            content_w, content_h = ss_img.size
            # Add shadow after transform so it doesn't get sheared/rotated with the device
            if template.screenshot.shadow:
                ss_img = add_shadow(ss_img, template.screenshot.shadow_blur, template.screenshot.shadow_opacity)

        shadow_pad = template.screenshot.shadow_blur * 2 if template.screenshot.shadow else 0

        offset_x = template.screenshot.offset_x if (template.device_frame and template.device_frame.enabled) else 0.0
        offset_y = template.screenshot.offset_y if (template.device_frame and template.device_frame.enabled) else 0.0

        # Device top-left without shadow
        dev_x = ss_x1 + (ss_w - content_w) // 2 + int(offset_x * ss_w / 2)
        dev_y = ss_y1 + (ss_h - content_h) // 2 + int(offset_y * ss_h / 2)

        # Clamp: allow partial off-canvas while keeping a minimum sliver visible
        dev_x = max(-(content_w - _DEVICE_MIN_SLIVER), min(width - _DEVICE_MIN_SLIVER, dev_x))
        dev_y = max(-(content_h - _DEVICE_MIN_SLIVER), min(height - _DEVICE_MIN_SLIVER, dev_y))

        sx = dev_x - shadow_pad
        sy = dev_y - shadow_pad

        result.paste(ss_img, (sx, sy), ss_img)

        if template.device_frame and template.device_frame.enabled:
            layout_info = {
                "device_x": dev_x,
                "device_y": dev_y,
                "device_w": content_w_visual,
                "device_h": content_h_visual,
                "ss_x1": ss_x1,
                "ss_y1": ss_y1,
                "ss_x2": ss_x2,
                "ss_y2": ss_y2,
                "corners": projected_corners(
                    template.device_frame.transform,
                    content_w_visual, content_h_visual,
                    content_w, content_h,
                    dev_x, dev_y,
                ),
            }

    return result.convert("RGB"), layout_info


def render_with_bounds(
    template: TemplateConfig,
    image_config: ImageConfig,
    project_root: Path,
) -> tuple[Image.Image, dict | None]:
    if template.layout == "hero":
        return render_hero(template, image_config, project_root)
    else:
        raise ValueError(f"Unknown layout: '{template.layout}'")


def render(
    template: TemplateConfig,
    image_config: ImageConfig,
    project_root: Path,
) -> Image.Image:
    img, _ = render_with_bounds(template, image_config, project_root)
    return img

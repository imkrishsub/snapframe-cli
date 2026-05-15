from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .config import FontConfig, ImageConfig, ScreenshotConfig, TemplateConfig


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
        return ImageFont.truetype(str(font_path), font_config.size)
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


def _load_screenshot(
    path: str,
    config: ScreenshotConfig,
    available_width: int,
    available_height: int,
    project_root: Path,
) -> tuple[Image.Image, tuple[int, int]]:
    img = Image.open(project_root / path).convert("RGBA")

    # Scale: target width = available_width * scale, capped by height
    target_w = int(available_width * config.scale)
    aspect = img.height / img.width
    target_h = int(target_w * aspect)

    max_h = int(available_height * 0.92)
    if target_h > max_h:
        target_h = max_h
        target_w = int(target_h / aspect)

    img = img.resize((target_w, target_h), Image.LANCZOS)
    content_size = (target_w, target_h)

    if config.rounded_corners > 0:
        img = apply_rounded_corners(img, config.rounded_corners)

    if config.shadow:
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

    # Measure lines
    line_metrics = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        lh = bbox[3] - bbox[1]
        line_metrics.append((lw, lh))

    line_h = max(lh for _, lh in line_metrics) if line_metrics else 0
    line_spacing = int(line_h * 0.3)
    total_text_h = len(lines) * line_h + max(0, len(lines) - 1) * line_spacing

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

    # Vertically center text within text region
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

    # Draw screenshot
    if has_screenshot:
        ss_img, (content_w, content_h) = _load_screenshot(
            image_config.screenshot,
            template.screenshot,
            ss_w,
            ss_h,
            project_root,
        )

        shadow_pad = template.screenshot.shadow_blur * 2 if template.screenshot.shadow else 0
        sx = ss_x1 + (ss_w - content_w) // 2 - shadow_pad
        sy = ss_y1 + (ss_h - content_h) // 2 - shadow_pad

        result.paste(ss_img, (sx, sy), ss_img)

    return result.convert("RGB")


def render(
    template: TemplateConfig,
    image_config: ImageConfig,
    project_root: Path,
) -> Image.Image:
    if template.layout == "hero":
        return render_hero(template, image_config, project_root)
    else:
        raise ValueError(f"Unknown layout: '{template.layout}'")

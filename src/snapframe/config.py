from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class BackgroundConfig:
    type: str = "gradient"
    colors: list[str] = field(default_factory=lambda: ["#667eea", "#764ba2"])
    angle: int = 135
    color: str = "#667eea"


@dataclass
class FontConfig:
    path: str = "assets/fonts/Inter-Bold.ttf"
    size: int = 56
    color: str = "#ffffff"
    align: str = "center"


@dataclass
class TextConfig:
    position: str = "top"


@dataclass
class ScreenshotConfig:
    enabled: bool = True
    rounded_corners: int = 16
    shadow: bool = True
    shadow_blur: int = 30
    shadow_opacity: float = 0.4
    scale: float = 0.70
    offset_x: float = 0.0
    offset_y: float = 0.0


@dataclass
class DeviceFrameTransformConfig:
    mode: str = "none"               # "none" | "tilt" | "iso" | "float"
    tilt_angle: float = -15.0        # degrees, -45 to +45
    iso_variant: str = "left"        # "left" | "right"
    float_preset: str = "left-lean"  # "left-lean" | "right-lean"


@dataclass
class DeviceFrameConfig:
    enabled: bool = False
    model: str = "iphone-15-pro"
    finish: str = "black"
    transform: DeviceFrameTransformConfig = field(default_factory=DeviceFrameTransformConfig)


@dataclass
class TemplateConfig:
    size: tuple[int, int] = (1200, 630)
    layout: str = "hero"
    padding: int = 60
    background: BackgroundConfig = field(default_factory=BackgroundConfig)
    font: FontConfig = field(default_factory=FontConfig)
    text: TextConfig = field(default_factory=TextConfig)
    screenshot: ScreenshotConfig = field(default_factory=ScreenshotConfig)
    device_frame: DeviceFrameConfig = field(default_factory=DeviceFrameConfig)


@dataclass
class ImageConfig:
    template: str = ""
    output: str = ""
    title: str = ""
    screenshot: str | None = None


@dataclass
class ProjectConfig:
    images: list[ImageConfig] = field(default_factory=list)


def _make_background(d: dict) -> BackgroundConfig:
    cfg = BackgroundConfig()
    if "type" in d:
        cfg.type = d["type"]
    if "colors" in d:
        cfg.colors = d["colors"]
    if "angle" in d:
        cfg.angle = d["angle"]
    if "color" in d:
        cfg.color = d["color"]
    return cfg


def _make_font(d: dict) -> FontConfig:
    cfg = FontConfig()
    if "path" in d:
        cfg.path = d["path"]
    if "size" in d:
        cfg.size = d["size"]
    if "color" in d:
        cfg.color = d["color"]
    if "align" in d:
        cfg.align = d["align"]
    return cfg


def _make_text(d: dict) -> TextConfig:
    cfg = TextConfig()
    if "position" in d:
        cfg.position = d["position"]
    return cfg


def _make_screenshot(d: dict) -> ScreenshotConfig:
    cfg = ScreenshotConfig()
    if "enabled" in d:
        cfg.enabled = d["enabled"]
    if "rounded_corners" in d:
        cfg.rounded_corners = d["rounded_corners"]
    if "shadow" in d:
        cfg.shadow = d["shadow"]
    if "shadow_blur" in d:
        cfg.shadow_blur = d["shadow_blur"]
    if "shadow_opacity" in d:
        cfg.shadow_opacity = d["shadow_opacity"]
    if "scale" in d:
        cfg.scale = d["scale"]
    if "offset_x" in d:
        cfg.offset_x = float(d["offset_x"])
    if "offset_y" in d:
        cfg.offset_y = float(d["offset_y"])
    return cfg


def _make_device_frame(d: dict) -> DeviceFrameConfig:
    cfg = DeviceFrameConfig()
    if "enabled" in d:
        cfg.enabled = d["enabled"]
    if "model" in d:
        cfg.model = d["model"]
    if "finish" in d:
        cfg.finish = d["finish"]
    if "transform" in d:
        t = d["transform"]
        tx = DeviceFrameTransformConfig()
        if "mode" in t:
            tx.mode = t["mode"]
        if "tilt_angle" in t:
            tx.tilt_angle = float(t["tilt_angle"])
        if "iso_variant" in t:
            tx.iso_variant = t["iso_variant"]
        if "float_preset" in t:
            tx.float_preset = t["float_preset"]
        cfg.transform = tx
    return cfg


def load_template(path: Path, project_root: Path) -> TemplateConfig:
    with open(path, "rb") as f:
        data = tomllib.load(f)

    cfg = TemplateConfig()

    if "size" in data:
        cfg.size = tuple(data["size"])

    if "layout" in data:
        cfg.layout = data["layout"]

    if "padding" in data:
        cfg.padding = data["padding"]

    if "background" in data:
        cfg.background = _make_background(data["background"])

    if "font" in data:
        cfg.font = _make_font(data["font"])

    if "text" in data:
        cfg.text = _make_text(data["text"])

    if "screenshot" in data:
        cfg.screenshot = _make_screenshot(data["screenshot"])

    if "device_frame" in data:
        cfg.device_frame = _make_device_frame(data["device_frame"])

    return cfg


def load_project(path: Path) -> ProjectConfig:
    with open(path, "rb") as f:
        data = tomllib.load(f)

    images = []
    for img_data in data.get("images", []):
        img = ImageConfig()
        if "template" in img_data:
            img.template = img_data["template"]
        if "output" in img_data:
            img.output = img_data["output"]
        if "title" in img_data:
            img.title = img_data["title"]
        if "screenshot" in img_data:
            img.screenshot = img_data["screenshot"]
        images.append(img)

    return ProjectConfig(images=images)

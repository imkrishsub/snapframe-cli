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


@dataclass
class TemplateConfig:
    size: tuple[int, int] = (1200, 630)
    layout: str = "hero"
    padding: int = 60
    background: BackgroundConfig = field(default_factory=BackgroundConfig)
    font: FontConfig = field(default_factory=FontConfig)
    text: TextConfig = field(default_factory=TextConfig)
    screenshot: ScreenshotConfig = field(default_factory=ScreenshotConfig)


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

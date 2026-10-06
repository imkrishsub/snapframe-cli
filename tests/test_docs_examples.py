"""Documentation examples tests.

Each test reproduces a TOML snippet from docs/configuration.md and verifies
it builds successfully. If the docs drift from the code, these tests fail.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner
from PIL import Image

from snapframe.cli import cli
from snapframe.config import load_template


def _make_screenshot(path: Path, width: int = 390, height: int = 844) -> None:
    """Write a minimal placeholder PNG to use as a screenshot in tests."""
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (width, height), color=(30, 30, 50))
    img.save(str(path), format="PNG")


@pytest.fixture()
def runner():
    return CliRunner()


def test_init_creates_documented_structure(runner, tmp_path):
    """The directory tree in getting-started.md must match what init produces."""
    result = runner.invoke(cli, ["init", str(tmp_path)])
    assert result.exit_code == 0

    # Every path listed in the annotated tree in getting-started.md
    assert (tmp_path / "snapframe.toml").is_file()
    assert (tmp_path / "templates" / "hero-og.toml").is_file()
    assert (tmp_path / "templates" / "hero-square.toml").is_file()
    assert (tmp_path / "templates" / "appstore" / "iphone-69.toml").is_file()
    assert (tmp_path / "templates" / "appstore" / "iphone-65.toml").is_file()
    assert (tmp_path / "templates" / "appstore" / "ipad-13.toml").is_file()
    assert (tmp_path / "templates" / "appstore" / "ipad-11.toml").is_file()
    assert (tmp_path / "assets" / "fonts").is_dir()
    assert (tmp_path / "assets" / "screenshots").is_dir()
    assert (tmp_path / "output").is_dir()


def test_minimal_project_example_builds(runner, tmp_path):
    """The minimal snapframe.toml from configuration.md must build successfully."""
    # Scaffold the full project structure (gets us the iphone-69 template)
    runner.invoke(cli, ["init", str(tmp_path)])

    # Create a placeholder screenshot at the path used in the docs example
    _make_screenshot(tmp_path / "assets" / "screenshots" / "app-screenshot.png")

    # Overwrite the default snapframe.toml that init created.
    # This is the minimal example from docs/configuration.md exactly.
    (tmp_path / "snapframe.toml").write_text(
        '[[images]]\n'
        'template   = "templates/appstore/iphone-69.toml"\n'
        'output     = "output/appstore/iphone-69-hero.png"\n'
        'title      = "Your headline here"\n'
        'subtitle   = "Optional tagline"\n'
        'screenshot = "assets/screenshots/app-screenshot.png"\n'
    )

    result = runner.invoke(cli, ["build", "--project", str(tmp_path / "snapframe.toml")])
    assert result.exit_code == 0

    out = tmp_path / "output" / "appstore" / "iphone-69-hero.png"
    assert out.exists()
    assert Image.open(out).format == "PNG"


def test_image_background_example_builds(runner, tmp_path):
    """The image background snippet from configuration.md must build successfully."""
    runner.invoke(cli, ["init", str(tmp_path)])
    _make_screenshot(tmp_path / "assets" / "backgrounds" / "desk.jpg", 1600, 1200)

    template = tmp_path / "templates" / "appstore" / "iphone-69.toml"
    text = template.read_text()
    start = text.index("[background]")
    end = text.index("\n[", start + 1)
    template.write_text(
        text[:start]
        + '[background]\n'
        'type = "image"\n'
        'path = "assets/backgrounds/desk.jpg"\n'
        'blur = 20\n'
        'dim  = 0.35\n'
        + text[end:]
    )
    (tmp_path / "snapframe.toml").write_text(
        '[[images]]\n'
        'template = "templates/appstore/iphone-69.toml"\n'
        'output   = "output/bg.png"\n'
        'title    = "Hello"\n'
    )

    result = runner.invoke(cli, ["build", "--project", str(tmp_path / "snapframe.toml")])
    assert result.exit_code == 0, result.output
    assert load_template(template, tmp_path).background.type == "image"
    assert (tmp_path / "output" / "bg.png").exists()


def test_full_template_example_parses(tmp_path):
    """The full annotated template from configuration.md must parse without error."""
    # Full example — matches the TOML block in the "Full example" section exactly
    template_path = tmp_path / "full-example.toml"
    template_path.write_text(
        'size    = [1320, 2868]\n'
        'layout  = "hero"\n'
        'padding = 100\n'
        '\n'
        '[background]\n'
        'type   = "gradient"\n'
        'colors = ["#667eea", "#764ba2"]\n'
        'angle  = 135\n'
        '\n'
        '[font]\n'
        'path  = "assets/fonts/Inter-Bold.ttf"\n'
        'size  = 80\n'
        'color = "#ffffff"\n'
        'align = "center"\n'
        '\n'
        '[text]\n'
        'position = "top"\n'
        '\n'
        '[screenshot]\n'
        'enabled         = true\n'
        'scale           = 0.85\n'
        'rounded_corners = 36\n'
        'shadow          = true\n'
        'shadow_blur     = 50\n'
        'shadow_opacity  = 0.5\n'
        'offset_x        = 0.0\n'
        'offset_y        = 0.0\n'
        '\n'
        '[device_frame]\n'
        'enabled = true\n'
        'model   = "iphone-16-pro"\n'
        'finish  = "black"\n'
        '\n'
        '[device_frame.transform]\n'
        'mode         = "tilt"\n'
        'tilt_angle   = -15.0\n'
        'iso_variant  = "left"\n'
        'float_preset = "left-lean"\n'
    )

    cfg = load_template(template_path, tmp_path)
    assert cfg.size == (1320, 2868)
    assert cfg.layout == "hero"
    assert cfg.padding == 100
    assert cfg.background.type == "gradient"
    assert cfg.background.colors == ["#667eea", "#764ba2"]
    assert cfg.font.color == "#ffffff"
    assert cfg.font.align == "center"
    assert cfg.text.position == "top"
    assert cfg.screenshot.scale == 0.85
    assert cfg.screenshot.rounded_corners == 36
    assert cfg.device_frame.enabled is True
    assert cfg.device_frame.model == "iphone-16-pro"
    assert cfg.device_frame.finish == "black"
    assert cfg.device_frame.transform.mode == "tilt"
    assert cfg.device_frame.transform.tilt_angle == -15.0
    assert cfg.device_frame.transform.iso_variant == "left"
    assert cfg.device_frame.transform.float_preset == "left-lean"


@pytest.mark.parametrize("mode,extra_toml", [
    ("none",  ""),
    ("tilt",  "tilt_angle = -15.0\n"),
    ("iso",   'iso_variant = "left"\n'),
    ("float", 'float_preset = "left-lean"\n'),
])
def test_transform_modes_build(runner, tmp_path, mode, extra_toml):
    """Each transform mode example from configuration.md must build successfully."""
    (tmp_path / "templates").mkdir()
    (tmp_path / "output").mkdir()
    _make_screenshot(tmp_path / "assets" / "screenshots" / "app-screenshot.png")

    # Project config
    (tmp_path / "snapframe.toml").write_text(
        '[[images]]\n'
        'template   = "templates/transform.toml"\n'
        f'output     = "output/transform-{mode}.png"\n'
        'title      = "Transform test"\n'
        'screenshot = "assets/screenshots/app-screenshot.png"\n'
    )

    # Template using a small canvas for speed; device_frame.transform matches the docs example
    (tmp_path / "templates" / "transform.toml").write_text(
        'size = [400, 800]\n'
        'layout = "hero"\n'
        'padding = 40\n'
        '[background]\ntype = "solid"\ncolor = "#111111"\n'
        '[font]\nsize = 40\ncolor = "#ffffff"\nalign = "center"\n'
        '[text]\nposition = "top"\n'
        '[screenshot]\nenabled = true\nscale = 0.7\n'
        '[device_frame]\nenabled = true\nmodel = "iphone-16-pro"\nfinish = "black"\n'
        f'[device_frame.transform]\nmode = "{mode}"\n{extra_toml}'
    )

    result = runner.invoke(cli, ["build", "--project", str(tmp_path / "snapframe.toml")])
    assert result.exit_code == 0

    out = tmp_path / "output" / f"transform-{mode}.png"
    assert out.exists()
    assert Image.open(out).format == "PNG"

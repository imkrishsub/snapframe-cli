"""Tests for the snapframe CLI: init and build commands."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from PIL import Image

from snapframe.cli import cli


# ── helpers ───────────────────────────────────────────────────────────────────

@pytest.fixture()
def runner():
    return CliRunner()


def _make_minimal_project(root: Path) -> None:
    """Write a minimal snapframe.toml with one image entry (no screenshot)."""
    (root / "templates").mkdir(parents=True, exist_ok=True)
    (root / "output").mkdir(parents=True, exist_ok=True)
    (root / "snapframe.toml").write_text(
        '[[images]]\n'
        'template = "templates/t.toml"\n'
        'output = "output/out.png"\n'
        'title = "Hello"\n'
    )
    (root / "templates" / "t.toml").write_text(
        'size = [200, 100]\n'
        'layout = "hero"\n'
        'padding = 20\n'
        '[background]\ntype = "solid"\ncolor = "#333333"\n'
        '[font]\nsize = 24\n'
        '[text]\nposition = "top"\n'
        '[screenshot]\nenabled = false\n'
    )


# ── init: directory and file creation ────────────────────────────────────────

def test_init_creates_snapframe_toml(runner, tmp_path):
    result = runner.invoke(cli, ["init", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / "snapframe.toml").exists()


def test_init_creates_hero_og_template(runner, tmp_path):
    runner.invoke(cli, ["init", str(tmp_path)])
    assert (tmp_path / "templates" / "hero-og.toml").exists()


def test_init_creates_hero_square_template(runner, tmp_path):
    runner.invoke(cli, ["init", str(tmp_path)])
    assert (tmp_path / "templates" / "hero-square.toml").exists()


def test_init_creates_appstore_iphone_69_template(runner, tmp_path):
    runner.invoke(cli, ["init", str(tmp_path)])
    assert (tmp_path / "templates" / "appstore" / "iphone-69.toml").exists()


def test_init_creates_appstore_iphone_65_template(runner, tmp_path):
    runner.invoke(cli, ["init", str(tmp_path)])
    assert (tmp_path / "templates" / "appstore" / "iphone-65.toml").exists()


def test_init_creates_appstore_ipad_13_template(runner, tmp_path):
    runner.invoke(cli, ["init", str(tmp_path)])
    assert (tmp_path / "templates" / "appstore" / "ipad-13.toml").exists()


def test_init_creates_appstore_ipad_11_template(runner, tmp_path):
    runner.invoke(cli, ["init", str(tmp_path)])
    assert (tmp_path / "templates" / "appstore" / "ipad-11.toml").exists()


def test_init_creates_assets_fonts_directory(runner, tmp_path):
    runner.invoke(cli, ["init", str(tmp_path)])
    assert (tmp_path / "assets" / "fonts").is_dir()


def test_init_creates_assets_screenshots_directory(runner, tmp_path):
    runner.invoke(cli, ["init", str(tmp_path)])
    assert (tmp_path / "assets" / "screenshots").is_dir()


def test_init_creates_output_directory(runner, tmp_path):
    runner.invoke(cli, ["init", str(tmp_path)])
    assert (tmp_path / "output").is_dir()


def test_init_exits_successfully(runner, tmp_path):
    result = runner.invoke(cli, ["init", str(tmp_path)])
    assert result.exit_code == 0


def test_init_creates_nonexistent_project_directory(runner, tmp_path):
    new_dir = tmp_path / "new_project"
    assert not new_dir.exists()
    result = runner.invoke(cli, ["init", str(new_dir)])
    assert result.exit_code == 0
    assert new_dir.is_dir()


def test_init_skips_existing_file_with_warning(runner, tmp_path):
    (tmp_path / "snapframe.toml").write_text("# existing\n")
    result = runner.invoke(cli, ["init", str(tmp_path)])
    assert result.exit_code == 0
    assert "Warning" in result.output
    assert (tmp_path / "snapframe.toml").read_text() == "# existing\n"


def test_init_does_not_overwrite_existing_template(runner, tmp_path):
    (tmp_path / "templates").mkdir(parents=True)
    existing = tmp_path / "templates" / "hero-og.toml"
    existing.write_text("# custom\n")
    runner.invoke(cli, ["init", str(tmp_path)])
    assert existing.read_text() == "# custom\n"


def test_init_output_mentions_next_steps(runner, tmp_path):
    result = runner.invoke(cli, ["init", str(tmp_path)])
    assert "Next steps" in result.output


# ── build: error cases ────────────────────────────────────────────────────────

def test_build_exits_1_when_project_not_found(runner, tmp_path):
    result = runner.invoke(cli, ["build", "--project", str(tmp_path / "missing.toml")])
    assert result.exit_code == 1


def test_build_prints_error_when_project_not_found(runner, tmp_path):
    result = runner.invoke(cli, ["build", "--project", str(tmp_path / "missing.toml")])
    assert "Error" in result.output


def test_build_prints_no_images_when_only_filter_matches_nothing(runner, tmp_path):
    _make_minimal_project(tmp_path)
    result = runner.invoke(
        cli, ["build", "--project", str(tmp_path / "snapframe.toml"), "--only", "nonexistent"]
    )
    assert result.exit_code == 0
    assert "No images" in result.output


# ── build: happy path ─────────────────────────────────────────────────────────

def test_build_produces_output_png(runner, tmp_path):
    _make_minimal_project(tmp_path)
    result = runner.invoke(cli, ["build", "--project", str(tmp_path / "snapframe.toml")])
    assert result.exit_code == 0
    assert (tmp_path / "output" / "out.png").exists()


def test_build_output_is_valid_png(runner, tmp_path):
    _make_minimal_project(tmp_path)
    runner.invoke(cli, ["build", "--project", str(tmp_path / "snapframe.toml")])
    img = Image.open(tmp_path / "output" / "out.png")
    assert img.size == (200, 100)


def test_build_creates_output_subdirectory(runner, tmp_path):
    _make_minimal_project(tmp_path)
    (tmp_path / "snapframe.toml").write_text(
        '[[images]]\n'
        'template = "templates/t.toml"\n'
        'output = "output/sub/nested/out.png"\n'
        'title = "Hello"\n'
    )
    runner.invoke(cli, ["build", "--project", str(tmp_path / "snapframe.toml")])
    assert (tmp_path / "output" / "sub" / "nested" / "out.png").exists()


def test_build_prints_done_on_success(runner, tmp_path):
    _make_minimal_project(tmp_path)
    result = runner.invoke(cli, ["build", "--project", str(tmp_path / "snapframe.toml")])
    assert "Done" in result.output


def test_build_only_filter_builds_matching_image(runner, tmp_path):
    _make_minimal_project(tmp_path)
    result = runner.invoke(
        cli, ["build", "--project", str(tmp_path / "snapframe.toml"), "--only", "out"]
    )
    assert result.exit_code == 0
    assert (tmp_path / "output" / "out.png").exists()


def test_build_only_filter_skips_non_matching_images(runner, tmp_path):
    # Two entries: out.png and skip.png; --only out should skip skip.png
    (tmp_path / "templates").mkdir(parents=True, exist_ok=True)
    (tmp_path / "output").mkdir(parents=True, exist_ok=True)
    (tmp_path / "templates" / "t.toml").write_text(
        'size = [200, 100]\nlayout = "hero"\npadding = 20\n'
        '[background]\ntype = "solid"\ncolor = "#333333"\n'
        '[font]\nsize = 24\n[text]\nposition = "top"\n'
        '[screenshot]\nenabled = false\n'
    )
    (tmp_path / "snapframe.toml").write_text(
        '[[images]]\ntemplate = "templates/t.toml"\noutput = "output/out.png"\ntitle = "A"\n\n'
        '[[images]]\ntemplate = "templates/t.toml"\noutput = "output/skip.png"\ntitle = "B"\n'
    )
    runner.invoke(
        cli, ["build", "--project", str(tmp_path / "snapframe.toml"), "--only", "out"]
    )
    assert (tmp_path / "output" / "out.png").exists()
    assert not (tmp_path / "output" / "skip.png").exists()


def test_build_handles_render_error_gracefully(runner, tmp_path):
    """A render error for one image must not crash the entire build."""
    _make_minimal_project(tmp_path)
    with patch("snapframe.cli.render", side_effect=RuntimeError("oops")):
        result = runner.invoke(cli, ["build", "--project", str(tmp_path / "snapframe.toml")])
    assert result.exit_code == 0
    assert "Error" in result.output


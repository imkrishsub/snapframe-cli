from __future__ import annotations

from pathlib import Path

import click

from .config import load_project, load_template
from .renderer import render


HERO_OG_TOML = """\
size = [1200, 630]
layout = "hero"
padding = 60

[background]
type = "gradient"
colors = ["#667eea", "#764ba2"]
angle = 135

[font]
path = "assets/fonts/Inter-Bold.ttf"
size = 56
color = "#ffffff"
align = "center"

[text]
position = "top"

[screenshot]
enabled = true
rounded_corners = 16
shadow = true
shadow_blur = 30
shadow_opacity = 0.4
scale = 0.70
"""

HERO_SQUARE_TOML = """\
size = [1080, 1080]
layout = "hero"
padding = 80

[background]
type = "gradient"
colors = ["#667eea", "#764ba2"]
angle = 135

[font]
path = "assets/fonts/Inter-Bold.ttf"
size = 64
color = "#ffffff"
align = "center"

[text]
position = "top"

[screenshot]
enabled = true
rounded_corners = 20
shadow = true
shadow_blur = 40
shadow_opacity = 0.4
scale = 0.75
"""

APPSTORE_IPHONE_67_TOML = """\
size = [1320, 2868]
layout = "hero"
padding = 100

[background]
type = "gradient"
colors = ["#667eea", "#764ba2"]
angle = 135

[font]
path = "assets/fonts/Inter-Bold.ttf"
size = 80
color = "#ffffff"
align = "center"

[text]
position = "top"

[screenshot]
enabled = true
rounded_corners = 36
shadow = true
shadow_blur = 50
shadow_opacity = 0.5
scale = 0.85
"""

APPSTORE_IPHONE_65_TOML = """\
size = [1284, 2778]
layout = "hero"
padding = 100

[background]
type = "gradient"
colors = ["#667eea", "#764ba2"]
angle = 135

[font]
path = "assets/fonts/Inter-Bold.ttf"
size = 80
color = "#ffffff"
align = "center"

[text]
position = "top"

[screenshot]
enabled = true
rounded_corners = 36
shadow = true
shadow_blur = 50
shadow_opacity = 0.5
scale = 0.85
"""

APPSTORE_IPAD_129_TOML = """\
size = [2064, 2752]
layout = "hero"
padding = 160

[background]
type = "gradient"
colors = ["#667eea", "#764ba2"]
angle = 135

[font]
path = "assets/fonts/Inter-Bold.ttf"
size = 96
color = "#ffffff"
align = "center"

[text]
position = "top"

[screenshot]
enabled = true
rounded_corners = 48
shadow = true
shadow_blur = 70
shadow_opacity = 0.5
scale = 0.80
"""

APPSTORE_IPAD_11_TOML = """\
size = [1488, 2266]
layout = "hero"
padding = 120

[background]
type = "gradient"
colors = ["#667eea", "#764ba2"]
angle = 135

[font]
path = "assets/fonts/Inter-Bold.ttf"
size = 88
color = "#ffffff"
align = "center"

[text]
position = "top"

[screenshot]
enabled = true
rounded_corners = 40
shadow = true
shadow_blur = 60
shadow_opacity = 0.5
scale = 0.80
"""

PROJECT_TOML = """\
[[images]]
template = "templates/hero-og.toml"
output = "output/hero-og.png"
title = "Your headline goes here"
screenshot = "assets/screenshots/your-screenshot.png"

[[images]]
template = "templates/hero-square.toml"
output = "output/hero-square.png"
title = "Your headline goes here"
screenshot = "assets/screenshots/your-screenshot.png"
"""


@click.group()
def cli():
    """Generate marketing images from screenshots and text."""


@cli.command()
@click.argument("project_dir", default=".", required=False)
def init(project_dir: str):
    """Initialize a new snapframe project."""
    root = Path(project_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)

    # Create directory structure
    for d in [
        root / "templates",
        root / "templates" / "appstore",
        root / "assets" / "fonts",
        root / "assets" / "screenshots",
        root / "output",
    ]:
        d.mkdir(parents=True, exist_ok=True)

    # Write files, skipping existing ones
    files = {
        root / "snapframe.toml": PROJECT_TOML,
        root / "templates" / "hero-og.toml": HERO_OG_TOML,
        root / "templates" / "hero-square.toml": HERO_SQUARE_TOML,
        root / "templates" / "appstore" / "iphone-67.toml": APPSTORE_IPHONE_67_TOML,
        root / "templates" / "appstore" / "iphone-65.toml": APPSTORE_IPHONE_65_TOML,
        root / "templates" / "appstore" / "ipad-129.toml": APPSTORE_IPAD_129_TOML,
        root / "templates" / "appstore" / "ipad-11.toml": APPSTORE_IPAD_11_TOML,
    }

    for path, content in files.items():
        if path.exists():
            click.echo(
                click.style(f"Warning: '{path.relative_to(root)}' already exists, skipping.", fg="yellow")
            )
        else:
            path.write_text(content)
            click.echo(f"  Created {path.relative_to(root)}")

    click.echo("")
    click.echo(click.style("Project initialized.", fg="green"))
    click.echo("")
    click.echo("Next steps:")
    click.echo("  1. Add a font to assets/fonts/ (e.g. Inter-Bold.ttf)")
    click.echo("  2. Add screenshots to assets/screenshots/")
    click.echo("  3. Edit snapframe.toml with your titles and screenshot paths")
    click.echo("  4. Run: snapframe build")


@cli.command()
@click.option("--project", default="snapframe.toml", show_default=True, help="Path to project TOML file.")
@click.option("--only", default=None, help="Filter images by output filename substring.")
def build(project: str, only: str | None):
    """Build all images defined in the project config."""
    project_path = Path(project).resolve()

    if not project_path.exists():
        click.echo(click.style(f"Error: project file not found: '{project_path}'", fg="red"), err=True)
        raise SystemExit(1)

    project_root = project_path.parent

    try:
        project_config = load_project(project_path)
    except Exception as e:
        click.echo(click.style(f"Error loading project config: {e}", fg="red"), err=True)
        raise SystemExit(1)

    images = project_config.images

    if only:
        images = [img for img in images if only in img.output]

    if not images:
        click.echo("No images to build.")
        return

    for image_config in images:
        output_label = image_config.output
        click.echo(f"Building {output_label}...")

        try:
            template_path = project_root / image_config.template
            template = load_template(template_path, project_root)

            output_path = project_root / image_config.output
            output_path.parent.mkdir(parents=True, exist_ok=True)

            img = render(template, image_config, project_root)
            img.save(str(output_path), format="PNG")

            click.echo(click.style(f"  Done -> {output_path}", fg="green"))

        except Exception as e:
            click.echo(click.style(f"  Error: {e}", fg="red"), err=True)


@cli.command()
@click.option("--host", default="127.0.0.1", show_default=True, help="Host to bind to.")
@click.option("--port", default=5000, show_default=True, help="Port to listen on.")
@click.option("--debug", is_flag=True, default=False, help="Enable debug mode.")
def serve(host: str, port: int, debug: bool):
    """Start the web UI."""
    from .server import app
    click.echo(f"Snapframe UI running at http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)

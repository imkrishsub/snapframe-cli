# Snapframe

Generate polished App Store screenshots and marketing images from plain screenshots and text. Use the CLI to automate batch builds, or the web UI for interactive design.

## Requirements

- Python 3.11+

## Installation

```bash
# macOS / Linux
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .

# Windows
python3.11 -m venv .venv
.venv\Scripts\activate
pip install -e .
```

## Quick Start

```bash
# 1. Scaffold a new project
snapframe init my-app

# 2. Drop your screenshots into my-app/assets/screenshots/
# 3. Drop a font (e.g. Inter-Bold.ttf) into my-app/assets/fonts/
# 4. Edit my-app/snapframe.toml with your titles and screenshot paths

# 5. Build
cd my-app
snapframe build
```

Output PNGs are written to `output/`.

## Commands

### `snapframe init [PROJECT_DIR]`

Scaffolds a new project directory with template TOML files and an empty asset structure.

```
PROJECT_DIR/
  snapframe.toml                     # project config (lists images to build)
  templates/
    hero-og.toml                     # 1200×630 OG image
    hero-square.toml                 # 1080×1080 square
    appstore/
      iphone-69.toml                 # iPhone 6.9" 1320×2868
      iphone-65.toml                 # iPhone 6.5" 1284×2778
      ipad-13.toml                   # iPad 13" 2064×2752
      ipad-11.toml                   # iPad 11" 1488×2266
  assets/
    fonts/                           # put TTF fonts here
    screenshots/                     # put your app screenshots here
  output/                            # rendered PNGs written here
```

If a file already exists it is left unchanged (a warning is printed).

### `snapframe build [OPTIONS]`

Renders all images defined in `snapframe.toml`.

| Option | Default | Description |
|--------|---------|-------------|
| `--project PATH` | `snapframe.toml` | Path to the project TOML file |
| `--only TEXT` | — | Only build images whose output filename contains this substring |

```bash
# Build everything
snapframe build

# Use a project file outside the current directory
snapframe build --project ~/projects/myapp/snapframe.toml

# Build a single image by filename substring
snapframe build --only iphone-69
```

### `snapframe serve [OPTIONS]`

Starts the interactive web UI for designing and exporting screenshots without writing TOML.

| Option | Default | Description |
|--------|---------|-------------|
| `--host TEXT` | `127.0.0.1` | Host to bind to |
| `--port INT` | `5174` | Port to listen on |
| `--debug` | off | Enable Flask debug mode |

```bash
snapframe serve
# Open http://127.0.0.1:5174 in your browser

# Expose on the local network
snapframe serve --host 0.0.0.0 --port 8080
```

## Project Config (`snapframe.toml`)

Each `[[images]]` entry defines one output PNG:

```toml
[[images]]
template  = "templates/appstore/iphone-69.toml"
output    = "output/appstore/iphone-69-hero.png"
title     = "Your headline here"
subtitle  = "Optional tagline"                   # optional
screenshot = "assets/screenshots/main.png"       # optional
```

## Template Config

A template TOML controls canvas size, layout, background, font, and screenshot display.

```toml
size    = [1320, 2868]   # width × height in pixels
layout  = "hero"         # only "hero" is currently supported
padding = 100

[background]
type   = "gradient"      # "gradient" | "solid"
colors = ["#667eea", "#764ba2"]
angle  = 135             # gradient angle in degrees

[font]
path  = "assets/fonts/Inter-Bold.ttf"
size  = 80
color = "#ffffff"
align = "center"         # "left" | "center" | "right"

[text]
position = "top"         # "top" | "bottom" | "left" | "right"

[screenshot]
enabled        = true
scale          = 0.85    # fraction of the screenshot region to fill
rounded_corners = 36     # corner radius in pixels (0 = square)
shadow         = true
shadow_blur    = 50
shadow_opacity = 0.5
offset_x       = 0.0    # nudge: -1.0 (full left) to +1.0 (full right)
offset_y       = 0.0    # nudge: -1.0 (full top)  to +1.0 (full bottom)

[device_frame]
enabled = true
model   = "iphone-16-pro"   # see Device Frame Models below
finish  = "black"            # "black" | "matte-gray" | "natural-titanium"

[device_frame.transform]
mode         = "tilt"       # "none" | "tilt" | "iso" | "float"
tilt_angle   = -15.0        # degrees (used when mode = "tilt")
iso_variant  = "left"       # "left" | "right" (used when mode = "iso")
float_preset = "left-lean"  # "left-lean" | "right-lean" (used when mode = "float")
```

### Text Position Layouts

| `position` | Text region | Screenshot region |
|------------|-------------|-------------------|
| `top`      | top 25%+ of canvas | remaining bottom |
| `bottom`   | bottom 25%+ of canvas | remaining top |
| `left`     | left 40% of canvas | right 60% |
| `right`    | right 40% of canvas | left 60% |

### Device Frame Models

| Model | Description |
|-------|-------------|
| `iphone-15` | iPhone 15 |
| `iphone-15-pro` | iPhone 15 Pro |
| `iphone-16` | iPhone 16 |
| `iphone-16-plus` | iPhone 16 Plus |
| `iphone-16-pro` | iPhone 16 Pro |
| `iphone-16-pro-max` | iPhone 16 Pro Max |
| `iphone-17` | iPhone 17 |
| `iphone-17-air` | iPhone 17 Air |
| `iphone-17-pro` | iPhone 17 Pro |
| `iphone-17-pro-max` | iPhone 17 Pro Max |
| `ipad-pro-11` | iPad Pro 11" |
| `ipad-pro-12-9` | iPad Pro 12.9" |

## Development

```bash
pip install -e ".[dev]"
pytest
```

Run against the included test fixture:

```bash
snapframe build --project test/post-xnapper.toml
# Inspect output in test/output/
```

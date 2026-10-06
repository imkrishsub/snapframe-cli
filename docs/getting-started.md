# Getting started

Generate polished App Store screenshots and marketing images from plain screenshots and text.

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

## Your first project

```bash
snaphaus init my-app
```

This creates:

```
my-app/
  snaphaus.toml                     # project config
  templates/
    hero-og.toml                     # 1200×630 OG image
    hero-square.toml                 # 1080×1080 square
    appstore/
      iphone-69.toml                 # iPhone 6.9" 1320×2868
      iphone-65.toml                 # iPhone 6.5" 1284×2778
      ipad-13.toml                   # iPad 13" 2064×2752
      ipad-11.toml                   # iPad 11" 1488×2266
  assets/
    fonts/                           # add TTF fonts here
    screenshots/                     # add app screenshots here
  output/                            # rendered PNGs written here
```

Then:

1. Drop a font (e.g. `Inter-Bold.ttf`) into `my-app/assets/fonts/`
2. Drop your app screenshots into `my-app/assets/screenshots/`
3. Edit `my-app/snaphaus.toml` — update titles and screenshot paths
4. Build:

```bash
cd my-app
snaphaus build
```

Output PNGs are written to `output/`.

## Commands

### `snaphaus init [PROJECT_DIR]`

Scaffolds a new project directory with starter TOML files and an empty asset structure.

`PROJECT_DIR` defaults to `.` if omitted. Existing files are left unchanged; a warning is printed for each one skipped.

### `snaphaus build [OPTIONS]`

Renders all images defined in `snaphaus.toml`.

| Option | Default | Description |
|--------|---------|-------------|
| `--project PATH` | `snaphaus.toml` | Path to the project TOML file |
| `--only TEXT` | — | Only build images whose output filename contains this substring |

```bash
# Build everything
snaphaus build

# Use a project file in a different directory
snaphaus build --project ~/projects/myapp/snaphaus.toml

# Rebuild one size without running all of them
snaphaus build --only iphone-69
```

---

For interactive design, live preview, and one-click App Store export, use the web UI at [snaphaus.app](https://snaphaus.app).

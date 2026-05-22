# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup

Requires Python 3.11+. Create and activate a virtual environment first:

```bash
python3.11 -m venv .venv
source .venv/bin/activate   # macOS/Linux
.venv\Scripts\activate      # Windows
pip install -e .
```

## Commands

| Task | Command |
|------|---------|
| Build all images | `snapframe build` |
| Build with custom project file | `snapframe build --project path/to/snapframe.toml` |
| Build filtered subset | `snapframe build --only hero-og` |
| Init a new project | `snapframe init [project_dir]` |
| Run against test fixtures | `snapframe build --project test/post-xnapper.toml` |

There is no automated test suite. Validate changes by running `snapframe build --project test/post-xnapper.toml` and inspecting `test/output/`.

## Architecture

The tool has three layers:

1. **CLI** (`src/snapframe/cli.py`) — entry point via Click. `init` scaffolds a new project directory; `build` loads configs and calls the renderer for each image entry.

2. **Config** (`src/snapframe/config.py`) — parses two kinds of TOML files using `tomllib`:
   - *Project file* (`snapframe.toml`) — an `[[images]]` array; each entry references a template, an output path, a title string, and an optional screenshot path.
   - *Template file* (e.g. `templates/hero-og.toml`) — defines canvas size, layout, background, font, text position, and screenshot display options.

3. **Renderer** (`src/snapframe/renderer.py`) — pure Pillow logic. `render()` dispatches on `template.layout`; only `"hero"` is implemented. `render_hero` builds the gradient background, wraps and draws the title text, loads and composites the screenshot (with optional rounded corners and drop shadow).

## Key data flow

```
snapframe.toml  -->  ProjectConfig (list of ImageConfig)
                         |
templates/*.toml --> TemplateConfig
                         |
                    render(template, image_config, project_root)
                         |
                    output/*.png
```

All paths in TOML files are relative to the directory containing the project TOML (`project_root`). Font paths are resolved relative to `project_root`; if the configured font is missing, the renderer falls back to known system fonts, then PIL's default.

## Text rendering notes

- `_sanitize_text` in `renderer.py` replaces common Unicode punctuation (em dashes, smart quotes, etc.) with ASCII equivalents before rendering, because many TTF fonts lack those glyphs.
- Text is word-wrapped to fit the text region width, then vertically centred within that region.
- Text alignment (`left`, `center`, `right`) is set in the template's `[font]` section.

## Layouts

Only `"hero"` layout exists. It splits the canvas into a text region and a screenshot region. The split direction is controlled by `[text] position`:
- `"top"` / `"bottom"` — horizontal split (text band above or below)
- `"left"` / `"right"` — vertical split (40 % text, 60 % screenshot)

Adding a new layout means adding a `render_<name>` function in `renderer.py` and a matching `elif` branch in `render()`.

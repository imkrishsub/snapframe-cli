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

## Quick start

```bash
# 1. Scaffold a new project
snapframe init my-app

# 2. Drop a font (e.g. Inter-Bold.ttf) into my-app/assets/fonts/
# 3. Drop your app screenshots into my-app/assets/screenshots/
# 4. Edit my-app/snapframe.toml with your titles and screenshot paths
# 5. Build
cd my-app
snapframe build
```

Output PNGs are written to `output/`.

## Documentation

- [Getting started](docs/getting-started.md) — installation, commands, and your first project
- [Configuration reference](docs/configuration.md) — all `snapframe.toml` and template TOML fields

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

---

For interactive design, live preview, and one-click App Store export, use the web UI at [snapframe.app](https://snapframe.app).

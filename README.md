# Snaphaus

Generate polished App Store screenshots and marketing images from plain screenshots and text. Use the CLI to automate batch builds, or the web UI for interactive design.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Ko-fi](https://img.shields.io/badge/Support-Ko--fi-FF5E5B?logo=ko-fi&logoColor=white)](https://ko-fi.com/krishsub)

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
snaphaus init my-app

# 2. Drop a font (e.g. Inter-Bold.ttf) into my-app/assets/fonts/
# 3. Drop your app screenshots into my-app/assets/screenshots/
# 4. Edit my-app/snaphaus.toml with your titles and screenshot paths
# 5. Build
cd my-app
snaphaus build
```

Output PNGs are written to `output/`.

## Documentation

- [Getting started](docs/getting-started.md) — installation, commands, and your first project
- [Configuration reference](docs/configuration.md) — all `snaphaus.toml` and template TOML fields

## Development

```bash
pip install -e ".[dev]"
pytest
```

Run against the included test fixture:

```bash
snaphaus build --project test/post-xnapper.toml
# Inspect output in test/output/
```

## Contributing

Bug reports and pull requests are welcome via [GitHub Issues](../../issues).

A few guidelines:

- **New config field?** Add it to `src/snaphaus/config.py`, document it in `docs/configuration.md`, and add a corresponding test in `tests/test_docs_examples.py`. The doc tests treat the docs as a contract — if the example in the docs doesn't build, the test fails.
- **New render feature?** Add tests in `tests/test_renderer.py`. There is no automated visual test — validate by running `snaphaus build --project test/post-xnapper.toml` and inspecting `test/output/`.
- **New CLI command?** Add tests in `tests/test_cli.py` using Click's `CliRunner`.

## License

MIT — see [LICENSE](LICENSE).

---

For interactive design, live preview, and one-click App Store export, use the web UI at [snaphaus.app](https://snaphaus.app). If snaphaus saves you time, consider [buying me a coffee](https://ko-fi.com/krishsub).

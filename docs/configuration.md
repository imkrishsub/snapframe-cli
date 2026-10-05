# Configuration reference

## Project file (`snapframe.toml`)

Each `[[images]]` entry defines one output PNG.

| Field | Required | Description |
|-------|----------|-------------|
| `template` | Yes | Path to the template TOML file (relative to the project file) |
| `output` | Yes | Output PNG path (relative to the project file) |
| `title` | Yes | Headline text rendered on the image |
| `subtitle` | No | Secondary text rendered below the title at smaller size |
| `screenshot` | No | Path to the app screenshot (relative to the project file) |

```toml
[[images]]
template   = "templates/appstore/iphone-69.toml"
output     = "output/appstore/iphone-69-hero.png"
title      = "Your headline here"
subtitle   = "Optional tagline"
screenshot = "assets/screenshots/app-screenshot.png"
```

Multiple `[[images]]` entries can share a template or reference different ones:

```toml
[[images]]
template = "templates/appstore/iphone-69.toml"
output   = "output/iphone-69.png"
title    = "Focus on what matters"

[[images]]
template = "templates/appstore/ipad-13.toml"
output   = "output/ipad-13.png"
title    = "Focus on what matters"
```

---

## Template file

A template TOML controls canvas size, layout, background, font, and screenshot display. Templates are reusable — multiple project entries can share the same template.

### Top-level fields

| Field | Default | Description |
|-------|---------|-------------|
| `size` | `[1200, 630]` | Canvas dimensions as `[width, height]` in pixels |
| `layout` | `"hero"` | Layout type — only `"hero"` is currently supported |
| `padding` | `60` | Canvas padding in pixels |

### `[background]`

| Field | Default | Description |
|-------|---------|-------------|
| `type` | `"gradient"` | `"gradient"` or `"solid"` |
| `colors` | `["#667eea", "#764ba2"]` | Two hex colors for gradient (start and end) |
| `angle` | `135` | Gradient angle in degrees |
| `color` | `"#667eea"` | Hex color for solid backgrounds |

**Gradient:**

```toml
[background]
type   = "gradient"
colors = ["#667eea", "#764ba2"]
angle  = 135
```

**Solid:**

```toml
[background]
type  = "solid"
color = "#1a1a2e"
```

**Curated palettes** (these are the same values used by the web UI color swatches):

| Name | Type | Colors | Angle |
|------|------|--------|-------|
| Purple Dream | gradient | `["#667eea", "#764ba2"]` | 135° |
| Rose Blush | gradient | `["#f093fb", "#f5576c"]` | 135° |
| Ocean Breeze | gradient | `["#4facfe", "#00f2fe"]` | 135° |
| Mint Fresh | gradient | `["#43e97b", "#38f9d7"]` | 135° |
| Sunset | gradient | `["#fa709a", "#fee140"]` | 135° |
| Soft Lavender | gradient | `["#a18cd1", "#fbc2eb"]` | 135° |
| Midnight Tide | gradient | `["#30cfd0", "#330867"]` | 135° |
| Golden Hour | gradient | `["#f7971e", "#ffd200"]` | 135° |
| Noir | solid | `"#0a0a0a"` | — |
| Dark Navy | solid | `"#162040"` | — |

### `[font]`

| Field | Default | Description |
|-------|---------|-------------|
| `path` | `"assets/fonts/Inter-Bold.ttf"` | Font path (relative to the project file). Falls back to system fonts if the file is missing. |
| `size` | `56` | Font size in pixels |
| `color` | `"#ffffff"` | Text color as hex |
| `align` | `"center"` | Text alignment: `"left"`, `"center"`, or `"right"` |

### `[text]`

| Field | Default | Description |
|-------|---------|-------------|
| `position` | `"top"` | Where text is placed relative to the screenshot |

**Position values:**

| Value | Text region | Screenshot region |
|-------|-------------|-------------------|
| `"top"` | Top portion of canvas | Remaining bottom |
| `"bottom"` | Bottom portion of canvas | Remaining top |
| `"left"` | Left 40% of canvas | Right 60% |
| `"right"` | Right 40% of canvas | Left 60% |

### `[screenshot]`

| Field | Default | Description |
|-------|---------|-------------|
| `enabled` | `true` | Whether to composite the screenshot onto the canvas |
| `scale` | `0.70` | Fraction of the screenshot region the image fills |
| `rounded_corners` | `16` | Corner radius in pixels (`0` = square) |
| `shadow` | `true` | Whether to render a drop shadow |
| `shadow_blur` | `30` | Shadow blur radius in pixels |
| `shadow_opacity` | `0.4` | Shadow opacity (`0.0`–`1.0`) |
| `offset_x` | `0.0` | Horizontal nudge: `-1.0` (full left) to `+1.0` (full right) |
| `offset_y` | `0.0` | Vertical nudge: `-1.0` (full top) to `+1.0` (full bottom) |

### `[device_frame]`

Composites the screenshot inside a hardware device frame before placing it on the canvas.

| Field | Default | Description |
|-------|---------|-------------|
| `enabled` | `false` | Whether to render a device frame |
| `model` | `"iphone-15-pro"` | Device model (see table below) |
| `finish` | `"black"` | Frame finish: `"black"`, `"matte-gray"`, or `"natural-titanium"` |

**Supported models:**

| Model | Device |
|-------|--------|
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

### `[device_frame.transform]`

Controls how the device frame is projected onto the canvas.

| Field | Default | Description |
|-------|---------|-------------|
| `mode` | `"none"` | Projection mode: `"none"`, `"tilt"`, `"iso"`, or `"float"` |
| `tilt_angle` | `-15.0` | Rotation angle in degrees; negative = counter-clockwise (used when `mode = "tilt"`) |
| `iso_variant` | `"left"` | Isometric face (used when `mode = "iso"`): `"left"` slopes down to the right, `"right"` slopes down to the left. Vertical edges stay vertical; the device keeps its original height |
| `float_preset` | `"left-lean"` | Floating device pose (used when `mode = "float"`): device turned 30° about its vertical axis with camera perspective. `"left-lean"` keeps the right edge nearest, `"right-lean"` the left edge. The near edge keeps full height; the width foreshortens |

**No transform:**

```toml
[device_frame.transform]
mode = "none"
```

**Simple tilt (2D rotation):**

```toml
[device_frame.transform]
mode       = "tilt"
tilt_angle = -15.0
```

**Isometric projection:**

```toml
[device_frame.transform]
mode        = "iso"
iso_variant = "left"
```

**Floating device:**

```toml
[device_frame.transform]
mode         = "float"
float_preset = "left-lean"
```

---

## Full example

Complete template with every section and inline comments:

```toml
size    = [1320, 2868]   # width × height in pixels (iPhone 6.9")
layout  = "hero"         # only "hero" is currently supported
padding = 100            # canvas padding in pixels

[background]
type   = "gradient"
colors = ["#667eea", "#764ba2"]
angle  = 135

[font]
path  = "assets/fonts/Inter-Bold.ttf"
size  = 80
color = "#ffffff"
align = "center"

[text]
position = "top"

[screenshot]
enabled         = true
scale           = 0.85
rounded_corners = 36
shadow          = true
shadow_blur     = 50
shadow_opacity  = 0.5
offset_x        = 0.0
offset_y        = 0.0

[device_frame]
enabled = true
model   = "iphone-16-pro"
finish  = "black"

[device_frame.transform]
mode         = "tilt"
tilt_angle   = -15.0
iso_variant  = "left"
float_preset = "left-lean"
```

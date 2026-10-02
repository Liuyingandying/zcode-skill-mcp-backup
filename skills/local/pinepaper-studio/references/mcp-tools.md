# PinePaper MCP Tools Reference

The `pinepaper-dev` MCP server exposes 120+ tools (prefixed `pinepaper_` / `pinepaper_agent_`).
This file is grounded in the **live tool schemas** — use these exact names and shapes.

## Creating items (the shape, not `createItem`)

Items are created differently per path — the operation `type` is `"create"` and the shape kind is
a separate `"itemType"` field; there's no combined `createItem`:

- **Inside `batch_execute`** (the normal MCP path): an operation object
  `{ "type": "create", "itemType": "circle", "position": {"x":540,"y":540}, "properties": {...} }`
- **Standalone MCP tool**: `pinepaper_create_item({ itemType, position, properties })`
- **Console / Paper.js path**: `app.create('circle', { x, y, ... })` (see `console-api.md`)

## The canonical Agent Mode workflow

1. **`pinepaper_agent_start_job`** — `{ clearCanvas:true, canvasPreset, description }`. Pass the
   user's prompt as `description` for creative direction. It returns the canvas size (use it to
   place items) and an ontology snapshot.
2. **`pinepaper_agent_batch_execute`** — **ONE call** containing ALL operations.
3. **`pinepaper_agent_end_job`** — returns a screenshot. Show/inspect it to validate.
4. **`pinepaper_agent_export`** — SVG / PNG / GIF / MP4 / WebM / PDF.

### ⚠️ The canvas is LIVE — never re-run the pipeline

Every operation executes immediately on the connected browser canvas. **Calling `batch_execute`
twice DOUBLES every item.** One `start_job`, one `batch_execute`, one `end_job`. To change things:
use `modify`/`delete` operations, or start a NEW job with `clearCanvas:true`.

## `batch_execute` — the 12 operation types (in order)

Each entry in `operations[]` has a `type` plus type-specific fields. Order matters:

```
CANVAS:  set_canvas_size {width,height | preset}  →  set_background {backgroundColor}  →  execute_generator {generatorName, generatorParams}
ITEMS:   create {itemType, position:{x,y}, properties}  →  modify {itemId, properties}  →  delete {itemId}
ANIMATE: animate {itemId, animationType, animationOptions}  →  keyframe_animate {itemId, keyframes, duration, loop}  →  relation {sourceId, targetId, relationType, relationOptions}
EFFECTS: apply_mask {itemId, maskPreset|maskType, maskOptions}  →  apply_effect {itemId, effectType, effectParams}
PLAY:    play_timeline {action:"play"|"stop"|"seek", time?, loop?}
```

**Item references:** use `"$0"`, `"$1"`, … to reference items by creation order within the same
batch (e.g. an `animate` op targets `itemId:"$0"`).

### Concrete example — animated "LIVE" badge (Instagram square)

```json
[
  { "type": "set_canvas_size", "preset": "instagram" },
  { "type": "set_background", "backgroundColor": "#0d1117" },
  { "type": "create", "itemType": "circle", "position": {"x": 470, "y": 540},
    "properties": { "radius": 18, "color": "#22c55e" } },
  { "type": "animate", "itemId": "$0", "animationType": "pulse",
    "animationOptions": { "speed": 1.5 } },
  { "type": "create", "itemType": "text", "position": {"x": 600, "y": 540},
    "properties": { "content": "LIVE", "fontSize": 54, "color": "#ffffff",
                    "fontFamily": "Arial, sans-serif", "fontWeight": "bold" } },
  { "type": "play_timeline", "action": "play" }
]
```

Then `pinepaper_agent_end_job` → inspect screenshot → `pinepaper_agent_export
{ platform:"instagram", format:"mp4" }` (or `format:"webm"`/`"gif"`).

### Authoritative enums (from the live schema)

- **animate `animationType`** (loop presets): `pulse`, `rotate`, `bounce`, `fade`, `wobble`,
  `slide`, `typewriter`. (These seven are what the simple `animate` op accepts.)
- **keyframe `easing`**: `linear`, `easeIn`, `easeOut`, `easeInOut`, `bounce`, `elastic`.
  Animatable properties: `x`, `y`, `scale`, `scaleX`, `scaleY`, `opacity`, `rotation`,
  `fillColor`, `strokeColor`, `fontSize`.
- **apply_effect `effectType`**: `sparkle`, `blast`, `smoke`, `fire`, `rain`, `snow`, `confetti`,
  `ripple`, `glow`, `electric`, `bubbles`, `dust`, `fireflies`, `shockwave`, `trail`.
- **execute_generator `generatorName`**: `drawSunburst`, `drawSunsetScene`, `drawGrid`,
  `drawWaves`, `drawCircuit`, `drawStackedCircles`, `drawPattern`, `drawBokeh`, `drawGradientMesh`,
  `drawGeometricAbstract`, `drawWindField`, `drawFluidFlow`, `drawOrganicFlow`, `drawNoiseTexture`,
  `drawGlobeWireframe`. (Prefer a generator over a flat background — much richer.)
- **relation `relationType`**: `orbits`, `follows`, `attached_to`, `points_at`, `mirrors`,
  `parallax`, `animates`, `grows_from`, `staggered_with`, `wave_through`, `circumscribes`,
  `morphs_to`, `group_morphs_to`, `moves_along_path`, `maintains_distance`, `bounds_to`,
  `indicates`, `camera_follows`, `camera_animates`.
- **apply_mask `maskPreset`** (reveal animations): `wipeLeft`, `wipeRight`, `wipeUp`, `wipeDown`,
  `iris`, `irisOut`, `star`, `heart`, `curtainHorizontal`, `curtainVertical`, `cinematic`,
  `diagonalWipe`, `revealUp`, `revealDown`. (`maskType` instead sets a static clip shape.)
- **`itemType`**: `text`, `circle`, `rectangle`, `star`, `triangle`, `polygon`, `ellipse`,
  `path`, `line`, `arc`.

A single item can carry a loop animation + keyframes + a relation + a mask + an effect at once.

## start_job `canvasPreset` values

`instagram` (1080×1080), `instagram-story` (1080×1920), `tiktok` (1080×1920), `youtube`
(1920×1080), `youtube-thumbnail`, `twitter` (1200×675), `linkedin`, `web`, `print-a4`,
`print-letter`. **There is no `instagram-square`** — use `instagram`. Default canvas (no preset)
is 800×600, so set a preset first for social/print work.

## Sizing & layout rules (the server enforces a vocabulary preflight)

- Keep all positions/sizes within ~5%–95% of canvas width/height (leave margins).
- Title `fontSize` ≤ ~5% of canvas width, body ≤ ~3%. (1080² → title ≤ 54, body ≤ 32.)
- **Never stack two text items at the same Y.** Give each a unique Y with spacing ≥ fontSize×1.4.
- `skipValidation:true` bypasses the ontology preflight — only set it when intentionally using
  experimental values.

## Diagrams are the exception — NOT batch_execute

Flowcharts/UML use their own tools: `pinepaper_create_diagram_shape` → `pinepaper_connect` →
`pinepaper_auto_layout`. Shapes: `process` (rect), `decision` (diamond), `terminal` (rounded),
`data`, `document`, `database`, `cloud`, `server`. (If your build exposes these under slightly
different names, confirm with `pinepaper_tool_guide({category:"diagram"})`.)

## Standalone tools (call directly, not inside batch)

- `pinepaper_deform` — vertex deformation presets (`fold`, `squeeze`, `twist`, `ripple`, `wave`,
  `breathe`, `wobble`…) with phase drivers (`sin`, `blink`, `pingpong`, `elastic`, `heartbeat`,
  `stepped`). Organic motion keyframes can't do.
- `pinepaper_create_chart` — bar/line/scatter/area; pass data as array of objects + options.
- `pinepaper_magic` — ontology-aware auto-animate (mood: calm/professional/energetic/dramatic/
  whimsical) or style remix.
- `pinepaper_physics` — rigid-body sim (init / add_body / apply_force / create_joint).
- `pinepaper_interaction` — continuous behaviors (repel/attract/follow/orbit/slingshot) + triggers.
- `pinepaper_sprite_sheet` — character/sprite pipelines (poses → play → export PNG + atlas).
- `pinepaper_measurement` — rulers, grid, snap-to-grid, item dimensions.
- Assets: `pinepaper_search_assets` → `pinepaper_import_asset` (850k+ SVG icons) for recognizable
  objects (planes, cars, animals, buildings); `pinepaper_import_svg`, `pinepaper_import_image`.
- Image detection (on-device, fully client-side; bbox detection over COCO-80, not pixel masks):
  `pinepaper_detect_objects` draws labeled boxes; with `{asNodes:true}` it promotes each detection
  to a typed, image-anchored **design node** (`pp:Detected*` aliased to a Wikidata entity, e.g.
  `pp:DetectedDog → wd:Q144`) and returns `nodes:[{id,label,ppType,wikidata}]`. To put a shape
  ON/AROUND a detected object so it tracks the image, `pinepaper_add_relation` from your shape to a
  node id with `follows` (on) / `circumscribes` (around) / `points_at` (arrow). `pinepaper_extract_object({label})`
  crops a detected region into a new raster.
- Dynamic text: set `contentType` on a text item to `clock`, `timer`, `countdown`, or `stopwatch`.

## Export — `pinepaper_agent_export`

Formats: `svg`, `png`, `gif`, `mp4`, `webm`, `pdf`. Quality: `draft` | `standard` | `high`.
Platform-aware (`{platform:"instagram"}` auto-picks; `{platform:"web", format:"svg"}` = animated
SVG). **When the user says "video", use `format:"mp4"`.** `framing:"camera"` renders only what a
`camera_animates` walkthrough frames (video formats only). Other exporters:
`pinepaper_export_svg`, `pinepaper_export_widget` (pp: ontology JSON),
`pinepaper_export_widget_html` (self-contained embeddable HTML).

## Error handling & a known conflict

If a tool or export fails, **report the real error** — do not silently fall back to HTML/CSS, a
React component, or another library; those are not PinePaper outputs, and don't retry an export in
a different format on failure. Note: the **`frontend-design` plugin** pushes agents toward HTML/CSS
pages, which conflicts with PinePaper; if generations keep coming out as HTML, suggest the user
disable that plugin.

# PinePaper Capability Catalog

Concrete menu of presets, effects, and formats. These values are grounded in the **live MCP
schema** (the authoritative source for the MCP path). PinePaper is beta (v0.5.x); if a value is
rejected, confirm the current set with `pinepaper_tool_guide`, `pinepaper_get_available_easings`,
or `pinepaper_list_generators`.

## Item types
`text`, `circle`, `rectangle`, `star`, `triangle`, `polygon`, `ellipse`, `path`, `line`, `arc`.
Text supports dynamic `contentType`: `clock`, `timer`, `countdown`, `stopwatch`.

## Loop animations (simple `animate`)
`pulse`, `rotate`, `bounce`, `fade`, `wobble`, `slide`, `typewriter`.
> The marketing site lists "10 loop animations" (adding shake/swing/jelly/scroll); those are editor
> UI presets, but the MCP `animate` operation accepts exactly the seven above. For anything beyond
> them, use `keyframe_animate`, a `relation`, or `pinepaper_deform`.

## Keyframe easings
`linear`, `easeIn`, `easeOut`, `easeInOut`, `bounce`, `elastic`. Animatable properties: `x`, `y`,
`scale`, `scaleX`, `scaleY`, `opacity`, `rotation`, `fillColor`, `strokeColor`, `fontSize`.

## Effects (`apply_effect`)
`sparkle`, `blast`, `smoke`, `fire`, `rain`, `snow`, `confetti`, `ripple`, `glow`, `electric`,
`bubbles`, `dust`, `fireflies`, `shockwave`, `trail`. Params (`effectParams`) commonly include
`color`, `speed`, `size`, `radius`, `count`.

## Mask reveals (`apply_mask` → `maskPreset`)
`wipeLeft`, `wipeRight`, `wipeUp`, `wipeDown`, `iris`, `irisOut`, `star`, `heart`,
`curtainHorizontal`, `curtainVertical`, `cinematic`, `diagonalWipe`, `revealUp`, `revealDown`.
(`maskType` instead applies a static clip shape such as `circle`, `rounded`, `hexagon`, `star`.)

## Vertex deformation (`pinepaper_deform`, standalone)
Presets: `fold`, `squeeze`, `twist`, `ripple`, `wave`, `breathe`, `wobble`, and more.
Phase drivers: `sin`, `blink`, `pingpong`, `elastic`, `heartbeat`, `stepped`.

## Generators (`execute_generator`) — prefer over flat backgrounds
`drawSunburst`, `drawSunsetScene`, `drawGrid`, `drawWaves`, `drawCircuit`, `drawStackedCircles`,
`drawPattern`, `drawBokeh`, `drawGradientMesh`, `drawGeometricAbstract`, `drawWindField`,
`drawFluidFlow`, `drawOrganicFlow`, `drawNoiseTexture`, `drawGlobeWireframe`.
By mood — dreamy/soft: Bokeh, GradientMesh, OrganicFlow · techy: Circuit, Grid, WindField ·
nature/warm: SunsetScene, Sunburst, Waves · abstract: GeometricAbstract, FluidFlow, NoiseTexture ·
decorative: Pattern, StackedCircles.

## Relation types (`relation`) — declarative behavior between items
`orbits`, `follows`, `attached_to`, `points_at`, `mirrors`, `parallax`, `animates`, `grows_from`,
`staggered_with`, `wave_through`, `circumscribes`, `morphs_to`, `group_morphs_to`,
`moves_along_path`, `maintains_distance`, `bounds_to`, `indicates`, `camera_follows`,
`camera_animates`. Great for solar systems (`orbits`), labels that track a moving object
(`attached_to`/`follows`), morph transitions (`morphs_to`), and camera moves (`camera_animates`).

## Diagrams (separate toolset — not batch_execute)
`pinepaper_create_diagram_shape` → `pinepaper_connect` → `pinepaper_auto_layout`.
Shapes: `process`, `decision`, `terminal`, `data`, `document`, `database`, `cloud`, `server`.

## Canvas presets (`canvasPreset` / `set_canvas_size` preset)
`instagram` (1080×1080), `instagram-story` (1080×1920), `tiktok` (1080×1920), `youtube`
(1920×1080), `youtube-thumbnail`, `twitter` (1200×675), `linkedin`, `web`, `print-a4`,
`print-letter`. Default canvas with no preset is 800×600. **There is no `instagram-square`.**

## Export formats — pick by intent
| Format | Best for |
|--------|----------|
| **mp4** | Video / social (use this whenever the user says "video") |
| **webm** | Highest-quality animation |
| **gif** | Quick shareable loop (Twitter animated default) |
| **svg** | Web embedding, animated SVG, crisp at any size (web platform default) |
| **png** | Static raster (static platform default) |
| **pdf** | Print |

Platform auto-mapping: instagram/story/tiktok/youtube → MP4 animated, PNG static; twitter → GIF
animated; web → SVG. Quality: `draft` / `standard` / `high`. Widget exports
(`export_widget` / `export_widget_html`) produce embeddable interactive output.

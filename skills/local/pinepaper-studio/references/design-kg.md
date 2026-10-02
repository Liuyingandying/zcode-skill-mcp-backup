# PinePaper design KG — what you can author

> **Generated** from `js/ontology/Vocabulary.js` + `assets/client-llm/generators.json`
> by `scripts/build-design-kg.js`. Do not edit by hand — re-run `npm run build:design-kg`.

This is the agent-facing projection of the PinePaper ontology (the `pp:`
design knowledge graph). Use it to ground what you BUILD — pick the right
item type, relation, generator, or animation from the real vocabulary instead
of guessing. The names below are the **exact engine strings** every drive path
accepts:

- **MCP:** the listed `pinepaper_*` tool, e.g. `create_item { itemType: "star" }`,
  `add_relation { relation: "orbits" }`, `execute_generator { generator: "drawWaves" }`.
- **Console / `window.PinePaper`:** `app.create("star", {…})`, `app.animate(item, { animationType: "pulse" })`,
  `app.addRelation(fromId, toId, "orbits", {…})`, `app.executeGenerator("drawWaves")`.
- **Standalone (no live editor):** emit scene JSON / widget HTML / Paper.js using these
  same type + relation names so the result round-trips into the editor and exports.

The machine-readable peer is `dist/ontology/index.ttl` (full Turtle/JSON-LD); this
file is the distilled, context-sized view.

## Item types (55)

Create with `pinepaper_create_item { itemType: "<name>" }` (or `app.create("<name>", {…})`)
unless another tool is noted.

| itemType | creates with | what it is |
|----------|--------------|------------|
| `arc` | `pinepaper_create_item` | An open curved path through three points — `from`, `through`, `to` — where the middle point sets the bulge. The curve is defined by geometry rather than by control handles, so it is the cheapest way to get a controlled curve without authoring béziers. Choose pp:Path for anything needing more than one bend. |
| `areaChart` / `areachart` | `pinepaper_create_chart` | Area chart — filled region under a line, showing volume and trends |
| `audio` | `pinepaper_media` | Audio media item — sample-buffer source with volume, gain, and timeline placement. May coexist with a video pp:MediaRef or stand alone. |
| `barChart` / `barchart` | `pinepaper_create_chart` | Bar chart — rectangular marks on Cartesian axes for categorical comparison |
| `causticsraster` | `—` | Refracted light patterns on a submerged surface. The anchor is the COMPUTER-GRAPHICS technique rather than the optics concept, because that is what this is — a rendering of caustics, not a measurement of them. |
| `character-eye` / `character-eyes` | `—` | A parametric eye: an outer silhouette, an optional pupil and a highlight, emitted under the eye_/pupil_ roles the expression system drives so it blinks and looks without further wiring. Not the anatomical organ — a drawn component of a character. |
| `circle` / `circle-outline` | `pinepaper_create_item` | The CURVE — every point at `radius` from the centre, drawn as a stroke with no interior. A circle has no width/height (passing them sizes it by the SMALLER of the two) and stays round under any scaling, where an ellipse with equal axes drifts the moment either is animated. Distinct from pp:Disk, the region this curve bounds: an item with the `circle` shape id is typed by what it PAINTS — `create('circle', { fillColor: null, strokeColor })` is a pp:Circle; `create('circle')` with any fill (the default) is a pp:Disk. Wikidata Q17278 is the curve, so this token is the outline, never the dot. Make one with the `circle-outline` shape id, whose default paint IS the curve; `regionType` points at the pp:Disk this curve bounds. |
| `closed-path` | `pinepaper_create_item` | Closed path (region/boundary) — encloses area, no start/end distinction. Functionally equivalent to a shape defined by its boundary equation. |
| `cloudsraster` | `—` | Drifting volumetric cloud cover over a sky gradient. Distinct from pp:CloudShape, which is a DIAGRAM symbol: one is weather, the other is a box you put text in, and a graph that conflated them would compose nonsense. |
| `compound-path` / `compoundpath` | `—` | Multiple sub-paths as single item (SVG imports, boolean ops) |
| `connector` | `pinepaper_connect` | An edge between two diagram shapes that re-routes as they move, with configurable `routing` (direct, orthogonal, curved), head and tail arrowheads and an optional label. It binds to PORTS, not coordinates — which is why it survives layout changes and why a plain pp:Line, which does not, is the wrong tool for joining nodes. |
| `diagram-shape` | `pinepaper_create_diagram_shape` | A flowchart, UML or network node — a shape that carries PORTS, so connectors attach to it and keep tracking it when it moves. That attachment is the whole difference from the plain shape of the same outline: choose this whenever anything will be connected to it, and a plain pp:Rectangle or pp:Ellipse when nothing will. |
| `disk` | `pinepaper_create_item` | The plane REGION bounded by a circle — the filled dot, orb or ball, defined by `radius` alone. What almost every round shape on a canvas is, and what `create('circle')` produces by default (the id has always drawn filled); `create('disk')` says so explicitly. Its boundary is a pp:Circle; the two are typed apart because a ring and a dot are different things to a screen reader, a training corpus and a boolean operation. Wikidata Q238231, the disk (mathematics), not Q17278 the curve. `boundaryType` points back at that curve; a filled circle is a disk because filling a circle is exactly what makes the region. |
| `ellipse` | `pinepaper_create_item` | A closed oval defined by independent `width` and `height`. Choose pp:Circle when the shape must remain round; use an ellipse precisely when the two axes should differ or animate apart. |
| `event` | `pinepaper_event` | Named event channel — pulsed by interaction relations (on_click_fire, etc.) and listened to by reaction relations (on_event_set_property, etc.). Carries optional payload (Numeric/String/Boolean/Pulse). Frame-coherent dispatch. |
| `group` | `—` | A container whose children transform, animate and export as one unit: moving, scaling or rotating the group applies to everything inside it. Selection resolves to the group, so click-through requires ⌥/Alt. Choose pp:Precomp instead when the contents need their OWN timeline — a group shares the scene's clock and cannot loop independently. |
| `image` / `raster` | `—` | A raster bitmap placed from `src` — pixels, not vectors, so it does not scale infinitely and cannot be morphed or path-animated. `crossOrigin` defaults to 'anonymous' so a CORS-friendly host keeps exports untainted; a non-CORS host fails VISIBLY as an empty slot rather than silently tainting every export of the scene. |
| `indexed-store` | `—` | Asynchronous structured storage, large enough for scene-sized state. Resolves LATER than the frame that asked, so it suits loading and saving rather than per-frame reads — that asynchrony is the whole reason it is a separate type from pp:LocalStore. |
| `intro-scene` | `—` | Motion scene configured for title reveals, openers, and intro presentation hooks. |
| `letterCollage` / `letter-collage` / `lettercollage` | `pinepaper_create_item` | Text rebuilt as per-letter artwork so each character can be styled independently — tiles, magazine cut-out, gradient fills. It REPLACES the text item, so apply it once the wording is settled; the letters are hit-tested by their ink, not by a bounding box. |
| `line` | `pinepaper_create_item` | An open two-point path from `from` to `to`, drawn with `strokeColor`/`strokeWidth` and NOT filled — a fill on an open path renders as the region between its endpoints, which is rarely what is wanted. Choose pp:Connector when the line joins two diagram nodes and should follow them; a plain line is fixed in place and will not. |
| `lineChart` / `linechart` | `pinepaper_create_chart` | Line chart — connected marks showing trends over a continuous axis |
| `local-store` | `—` | Synchronous key/value storage of strings, around 5 MB. Readable and writable during a frame, which is why a counter can increment on click and be read in the same tick. Shares the HOST PAGE's origin, so keys are namespaced and nothing private belongs here. |
| `marker` | `pinepaper_map_regions` | A pin drawn on a map at a geographic coordinate. Deliberately UNANCHORED: `anchor` compiles to rdfs:subClassOf, and a marker is a graphical annotation that POINTS AT a place — it is not one. Asserting schema:Place would publish that every marker has an address and real-world coordinates, when what it has is a fill colour and a canvas position. |
| `motion-scene` | `—` | Dynamic 2.5D vector motion canvas scene containing animation, procedural backgrounds, shaders, and audio synthesis. |
| `mountainsraster` / `formularaster` / `shaderraster` | `—` | A full-canvas surface whose pixels are COMPUTED rather than drawn — a generator's output, materialized as one raster the registry holds under its own id. It is a PLACE, not a decoration, and that distinction is the reason it is a node at all: a tunnel is a thing you can put something inside, so a rigged figure can run through one and a boat can sit on an ocean. A pp:ShaderEffectRelation, by contrast, is applied TO an item and dies with it. NOISE PROVENANCE: these programs call the SHARED pp:ShaderNode primitives from js/gpu/AuraNoiseGLSL.js, so a walk can descend from a field to the maths that draws it. Each used to inline its own hash and value noise — a third family beside the original auras' inline set and the shared one — which meant no usesShaderNode edge could be declared for any of them; that was corrected 2026-09-11 by porting them onto the shared module. pp:OceanField and pp:TunnelField declare no edge and that is not an omission: one is a sum of sine waves and the other a rotation, and neither hashes anything. |
| `oceanraster` | `—` | Animated water surface with depth-graded colour and a sun glint. Anchored to the ocean as a thing, so a walk can compose over it — a boat ON an ocean is a relation between two nodes, which it cannot be if the water is only a property of the canvas. |
| `open-path` | `pinepaper_create_item` | Open path (trajectory/stroke) — has start and end points, does not enclose area. Defined by curveType: the mathematical function governing its segments. |
| `outro-scene` | `—` | Motion scene configured for call-to-action, summaries, and closing presentation frames. |
| `path` | `pinepaper_create_item` | Vector path — semantically incomplete without open/closed distinction. Defined by its curveType (mathematical function family). Refined to OpenPath or ClosedPath during graph extraction. |
| `pattern` | `pinepaper_create_item` | Repeating decorative field (scanlines, stripes, grid, dots) materialized as ONE item — a single CompoundPath tiling an area. The scale-safe form of what would otherwise be hundreds of individual primitives. |
| `plasmaraster` | `—` | Domain-warped fractal noise through a cosine palette — the demoscene plasma, which is what the anchor names: a DEMO EFFECT, not the physical state of matter (that is a different Wikidata concept and anchoring to it would be a category error a model would then repeat). |
| `polygon` | `pinepaper_create_item` | A regular N-sided shape defined by `sides` (3 or more) and `radius` — every side and interior angle equal. Choose pp:Path when the outline is irregular; a polygon cannot express one, and forcing it produces a shape that silently ignores the vertices you meant. |
| `precomp` | `pinepaper_precomp` | A nested composition with its OWN timeline, so its contents can loop independently of the scene clock. That local clock is the whole difference from pp:Group, which shares the scene's time and cannot. |
| `rectangle` | `pinepaper_create_item` | A closed four-sided shape defined by `width` and `height`, with optional `cornerRadius` for rounded corners. The default container for panels, cards, bars and backdrops. Choose pp:DiagramShape instead when the rectangle is a NODE that connectors should attach to — a plain rectangle has no ports, so a connector aimed at it will not track it. |
| `region` | `pinepaper_map` | A rendered region shape on a map, filled and selectable. Unanchored for the same reason as pp:Marker: the drawn polygon DEPICTS an administrative area, it is not one, and rdfs:subClassOf would say it is. |
| `rigged-character` | `—` | A character whose parts are bound to a skeleton, so a pose or a walk cycle drives the artwork. Anchored on skeletal animation — the technique that defines it. |
| `scatterPlot` / `scatterplot` | `pinepaper_create_chart` | Scatter plot — point marks encoding two quantitative variables as position |
| `sound` | `—` | A synthesized audio source in the graph — a named voice whose value is a continuous waveform signal (ExpressionIR) over a [t0,t1] window, rendered by the Web Audio renderer. The synthesis counterpart to the sample-based pp:AudioClip; can hold a single tone, a chord, or an arbitrary partial set. |
| `star` | `pinepaper_create_item` | Star shape (geometrically: concave polygon with alternating radii) |
| `starfieldraster` | `—` | Multi-layer parallax starfield with hash-distributed, twinkling stars. Anchored to NOTHING on purpose: 'star field' as a rendered motif has no clean Wikidata concept — the searches return albums and video games — and a plausible-looking wrong anchor is worse than none, because the graph is training data and a wrong anchor is believed. |
| `text` | `pinepaper_create_item` | A run of characters rendered as vector glyphs, sized by `fontSize` and set in `fontFamily`. The only type whose content is language, so it carries the scene's meaning and is what a screen reader announces. `contentType` makes it LIVE — clock, timer, countdown, stopwatch — updating itself without any animation attached. Becomes pp:LetterCollage when a Text Style is applied and pp:TextEffect when split per character; both REPLACE the text item, so reach for them last. |
| `text-effect` | `—` | A character-level text animation: one text item decomposed into per-character glyphs that arrive under a named effect (scattered, matrix, decrypt…). The composition is addressed through its ROOT glyph, which carries the content, font and origin it was built from — so the effect can be changed without retyping the text. |
| `text-effect-glyph` | `—` | One character of a pp:TextEffect. An ordinary text item with its own keyframes; it points back at the composition root through pp:glyphOf, which is what lets the whole effect be re-targeted or removed as a unit. |
| `transition-scene` | `—` | Motion scene configured as a dynamic transition layer or section break. |
| `triangle` | `pinepaper_create_item` | A closed three-sided shape. Beyond `width`/`height` it accepts `kind` — right, equilateral, isosceles, obtuse, acute, scalene — or an explicit `angles` array, so the shape can be specified by its geometry rather than by computing vertices. Angles that nearly sum to 180 are normalised rather than refused. |
| `tunnelraster` | `—` | An infinite perspective tunnel. The clearest case for fields being nodes: 'a figure running inside the tunnel' is a relation between a rigged skeleton and this, and there is no way to say it if the tunnel is a property rather than a thing. |
| `unclassified` | `—` | Item type not expressible in current vocabulary. Enables vocabulary gap discovery — count and inspect unclassified items to identify missing types. |
| `video` | `pinepaper_media` | Video media item — frame-sampled raster source with playhead, in/out trim, and optional per-frame GPU filters. Referenced by pp:MediaRef handle. |
| `voronoiraster` | `—` | Cellular partition of the plane by nearest feature point. The anchor is the Voronoi diagram itself, the mathematics the image IS rather than a lookalike. |
| `world-character` | `pinepaper_world3d` | A controllable body in a 3D world — walks, jumps and collides with the terrain. Drivable by keyboard, timeline, relations or an agent. |
| `world-light` | `—` | A point light placed in a 3D world: a position, a colour, an intensity and a RANGE at which its contribution reaches exactly zero. A light as an OBJECT rather than a constant — addressable, so a relation can move it and a lamp that follows a character is an edge rather than a special case in the renderer. Casts no shadow: each shadow-casting light doubles the geometry passes, and the sun remains the single directional caster. |
| `world-material` | `—` | A named, SHARED surface description referenced by many world objects: one node, many users, so a single edit restyles all of them. That sharing is the whole point — a per-object colour already existed, and a material that styled one thing would be a rename rather than a capability. Carries colour and emissive, and — since js/world3d/PBR.js landed a real Cook-Torrance GGX BRDF — metalness and roughness, in Three.js's names and with Three.js's defaults, so a material authored against Three, Blender or Substance means the same thing here. WHERE THEY ACTUALLY RENDER is the part an agent must not guess: metalness and roughness reach the shader ONLY on the mesh path (addWorldMesh, and imported OBJ/glTF, which ride them through the uniforms bag into DEFAULT_MESH_FRAG). A plain pp:WorldObject — a box or a scattered prop — is drawn by PART_FRAG/PROP_FRAG, which shade with the older lambert term and declare no such uniform, so a material's metalness on a box is stored, listed and ignored. emissiveIntensity IS read: World3D scales the material's emissive by it before the frame is built, so it reaches every path that draws emissive. aoMapIntensity, normalScale and envMapIntensity have been REMOVED — each one scales a MAP, and there is no aoMap, no normalMap and no envMap; a knob that scales nothing is the claim-about-nothing defect wearing a Three.js name, and being Three's spelling does not make it real. They come back with the maps they scale, together, and not before. (This sentence previously said all four were accepted-but-inert. That was true when written and false from the moment emissiveIntensity was wired and the other three deleted; it is corrected here rather than quietly dropped, because a drifted claim is worse than a missing one.) clearcoat, clearcoatRoughness, sheenColor and sheenRoughness are REAL on the mesh path and carry Three's names and Three's defaults, which are inert: clearcoat 0 and a black sheenColor mean a material authored before they existed lights identically. Clearcoat is a second, always-DIELECTRIC specular lobe with its own roughness — a clearcoated metal shows a white highlight over a coloured one, which is what separates a coat from extra gloss — and it ATTENUATES the base beneath it, because light the coat reflects never reaches the base. Sheen is the Charlie retroreflective lobe that peaks at GRAZING angles, where GGX cannot reach at any roughness; it is what makes cloth read as cloth. Both are additive over the same Cook-Torrance evaluation and, like metalness and roughness, reach the shader ONLY on the mesh path. transmission, ior, thickness and opacity are ABSENT, and for one shared reason rather than as an oversight: each needs depth-sorted transparency, which this renderer does not have. They are named here so an agent learns the GATE rather than guessing the knob was forgotten. setMaterial patches colour, emissive, metalness, roughness, emissiveIntensity, clearcoat, clearcoatRoughness, sheenColor and sheenRoughness. Anchored to nothing: a plausible-looking Wikidata concept would be worse than none. |
| `world-mesh` | `—` | Geometry in a 3D world drawn by an author-supplied vertex and fragment program. Unlike pp:WorldObject, which is a box with a colour, its SHAPE and its SHADING are both the author's: vertices and triangles supplied as data, transformed by a vertex program that may displace them per frame. A registry citizen under its own id, so relations can target it — anchor a label to a procedural surface, or drive its uniforms from an event. |
| `world-object` | `pinepaper_world3d` | An object placed at chosen coordinates in a 3D world, as opposed to procedurally scattered. |

## Relations (140) — the behavior graph

Wire behavior between items with `pinepaper_add_relation { from, to, relation: "<name>", params }`
(or `app.addRelation(fromId, toId, "<name>", params)`). Relations are the canonical
behavior surface — prefer them over hand-rolled motion. Only relate items that exist.

| relation | direction | what it does |
|----------|-----------|--------------|
| `aligned_with` | source aligned to target on one axis | One axis (x or y) of the source center matches the target center; the other axis stays free (partial write). Params: axis (required), offset. |
| `anchored_in_world` | self-relation: source follows a world coordinate | A 2D item tracks a point in a 3D world (pp:World3D), projected onto the canvas — labels, markers and callouts that follow a character or a place as the camera moves. Use to caption, annotate or attach UI to 3D content. _(self-relation: omit target)_ |
| `animates` | self-relation: annotates the item | The item animates its own properties over time from keyframes. The relation form of a keyframe track, so that an item having timed behaviour is a fact the graph can be QUERIED for rather than something only the item itself knows. _(self-relation: omit target)_ |
| `attached_to` | source locked to target + offset | Rigid parent-child transform — source moves with target instantly via fixed offset. Zero-lag variant of follows. Use for labels, attachments, child objects. |
| `attached_to_tail` | port → arrow | A diagram port is bound to an arrow's TAIL, so the connector's start follows the item as it moves. Half of what makes a flowchart survive being rearranged. |
| `attracts` | source → target | The source moves toward the target when it comes within range, stops short of it, and eases back to where it was when the target leaves. Params: force, maxDistance, minDistance, maxSpeed, returnSpeed. The mirror of pp:repels, but not simply a negative force: approaching a target overshoots and oscillates without a speed cap and a stopping distance. |
| `below` | source placed below target | Source top edge sits on target bottom edge (mirror of on_top_of). Params: gap, align, overhang. |
| `beside` | source flanks target horizontally | Source is placed to the left or right of the target. Params: side (left/right), gap, align (top/center/bottom). |
| `blend_reacts_to` | source blend mode reacts to proximity of target | Source blend mode changes when target enters proximity / state. Use for collision-triggered visuals, reactive composition. |
| `blend_transition` | self-relation: source cycles blend modes over time | Source cycles through blend modes on a timed loop. Use for animated mood shifts, rhythmic visual changes. _(self-relation: omit target)_ |
| `bone_attached` | source item attached to target bone | Source canvas item rides a skeleton bone — inherits its transform. Use for character props, weapons, accessories on a rig. |
| `bone_skinned` | self-relation: source path skinned to skeleton (target=null) | Source path is skinned to a skeleton — each vertex deforms by linear blend of nearby bones' transforms. Contrast with attached_to (rigid follow) and bone_attached (inherits one bone's transform): this is per-vertex deformation enabling cloth, capes, soft-tissue. Stored as one self-edge per skinned path; the per-vertex weights live on the path's segments. _(self-relation: omit target)_ |
| `bounds_to` | source clamped within target bounds | Source's position is clamped within target's bounds. Use for keeping characters inside a frame or viewport-bounded motion. |
| `camera_animates` | viewport animates via keyframes (target=null) | Camera viewport interpolates between keyframed positions. Use for choreographed pans / zooms, fly-throughs, scripted shots. |
| `camera_follows` | viewport follows target item | Camera viewport tracks target's position with smooth pursuit. Use for cinematic follow shots, subject-lock cameras. |
| `centered_on` | source center on target center | Source center = target center + offset. Concentric when offset is 0 (use for concentric rings). Params: offsetX, offsetY. |
| `circumscribes` | source draws bounding shape around target (note: source=drawn shape, target=bounded item) | Source's bounds scale to fully enclose target. Use for halo highlights, selection rings, labels framing content. |
| `composed_as` | self-relation: annotates the item | ANNOTATION: this item is the root of a composition built from a named pattern. Carries the pattern key. Inert — it moves nothing; it records WHAT the arrangement is so the composition can be recognised, re-applied or queried later. _(self-relation: omit target)_ |
| `concentric_with` | source center = target center | Source's center is held on the target's center (shared center / concentric). |
| `connects_to` | diagram | A generic connection between diagram shapes when no notation-specific meaning applies. Prefer a specific subtype where one fits — the specific edge carries meaning into the exported graph, this one carries only adjacency. |
| `construction_reveal` | self-relation: source reveals at step time (target=null) | Self-relation: source fades in (opacity 0→1) starting at params.revealAt over params.fadeIn seconds, driven by the timeline (playbackTime). Used by pp:ConstructionSequence to play a construction back one step at a time. _(self-relation: omit target)_ |
| `contained_in_place` | source → region | The item is visually constrained within a map region, following schema.org/containedInPlace. States belonging rather than position: the item stays inside its region through re-projection and re-layout, without anyone recomputing coordinates. |
| `deform_breathe` | self-relation: breathe deformation on source | Item rhythmically scales in and out. Use for living / idle motion, organic presence. _(self-relation: omit target)_ |
| `deform_bulge` | self-relation: bulge deformation on source | Item bows outward from center. Use for inflation, swelling, expansion. _(self-relation: omit target)_ |
| `deform_fluid_bleed` | self-relation: fluid capillary paper bleed on source | Item vertices diffuse outward into capillary paper-grain fibers like wet ink. Use for sketch art, watercolor bleeding, and fluid dispersion. _(self-relation: omit target)_ |
| `deform_fold` | self-relation: fold deformation on source | Item creases along a fold line and lays flat. Use for paper-fold animations, panel reveals. _(self-relation: omit target)_ |
| `deform_inflate` | self-relation: inflate deformation on source | Item swells uniformly outward. Use for balloon, pre-pop state, growth. _(self-relation: omit target)_ |
| `deform_melt` | self-relation: melt deformation on source | Item droops downward as if liquefying. Use for dissolution, dali-esque scenes, decay. _(self-relation: omit target)_ |
| `deform_pinch` | self-relation: pinch deformation on source | Item draws toward a central point. Use for vacuum-up, focus pull, gravity well. _(self-relation: omit target)_ |
| `deform_ripple` | self-relation: ripple deformation on source | Item's surface ripples with concentric waves. Use for water disturbance, energy pulse on shape. _(self-relation: omit target)_ |
| `deform_shear` | self-relation: shear deformation on source | Item slants progressively along one axis. Use for italic-like lean, motion shear, gravity drag. _(self-relation: omit target)_ |
| `deform_squash` | self-relation: squash deformation on source | Item flattens vertically and stretches horizontally (area-preserving). Use for bounce-landing impact, weight. _(self-relation: omit target)_ |
| `deform_squeeze` | self-relation: squeeze deformation on source | Item pinches inward symmetrically. Use for cartoon expression, compression visuals. _(self-relation: omit target)_ |
| `deform_twist` | self-relation: twist deformation on source | Item rotates progressively along an axis. Use for whirlpool, candy-cane, screw motion. _(self-relation: omit target)_ |
| `deform_wave` | self-relation: wave deformation on source | Item undulates with a traveling sine wave. Use for flag-waving, fabric, liquid surface. _(self-relation: omit target)_ |
| `deform_wobble` | self-relation: wobble deformation on source | Item jiggles asymmetrically like jelly. Use for playful, liquid, unstable motion. _(self-relation: omit target)_ |
| `driven_by` | source property driven by target property | Source property linearly maps from a target property. Use for parameter linking, slaved values, reactive controls. |
| `effect_blast` | self-relation: blast burst on source | Outward radial burst of particles emits once. Use for impacts, explosions, energy release. _(self-relation: omit target)_ |
| `effect_bubbles` | self-relation: rising bubbles on source | Rising bubbles emerge from the item. Use for underwater, liquid, light-hearted scenes. _(self-relation: omit target)_ |
| `effect_caustics` | self-relation: water caustic light network on source | The network of focused light under a moving water surface, brightest where the wave curvature converges. Use for pools, submersion, aquaria, dappled light. APPLIED WITH applyEffect(item, 'caustics'), NOT addRelation: owned by ItemAuraSystem and persisted on item.data.aura. _(self-relation: omit target)_ |
| `effect_confetti` | self-relation: confetti burst on source | Colored streamers fall from above. Use for celebrations, accomplishments, party scenes. _(self-relation: omit target)_ |
| `effect_dust` | self-relation: ambient dust on source | Slowly drifting dust motes fill the area. Use for old / abandoned moods, sunbeam visualizations. _(self-relation: omit target)_ |
| `effect_electric` | self-relation: electric bolts on source | Crackling electric arcs jump around the item. Use for energy, danger, sci-fi power. _(self-relation: omit target)_ |
| `effect_electric_arc` | self-relation: branching discharge filaments over source | Branching electrical discharge filaments with a hot core and an inverse-square bloom. Use for energy, danger, machinery under load, storm. APPLIED WITH applyEffect(item, 'electric_arc'), NOT addRelation: owned by ItemAuraSystem and persisted on item.data.aura. _(self-relation: omit target)_ |
| `effect_fire` | self-relation: fire particles on source | Animated flame emerges from the item. Use for heat, burning, energy. _(self-relation: omit target)_ |
| `effect_fireflies` | self-relation: firefly particles on source | Slow-blinking glowing particles drift around the item. Use for magical night scenes, romantic ambiance. _(self-relation: omit target)_ |
| `effect_gem_smoke` | self-relation: volumetric curling smoke wreath on source | Volumetric curling smoke wreath encircles the item silhouette. Use for ornate emphasis, ritual or magical contexts. APPLIED WITH applyEffect(item, 'gem_smoke'), NOT addRelation: unlike the particle effects beside it this is a shader aura owned by ItemAuraSystem and persisted on item.data.aura, so no effect_gem_smoke rule is registered and addRelation would no-op silently. _(self-relation: omit target)_ |
| `effect_glow` | self-relation: pulsing glow aura on source | Soft luminous halo surrounds the item. Use for highlighting, importance, magical quality. _(self-relation: omit target)_ |
| `effect_heatmap` | self-relation: animated thermal halo turbulence on source | Animated thermal-color noise fills the item's silhouette. Use for temperature visualization, dramatic glow, abstract energy. APPLIED WITH applyEffect(item, 'heatmap'), NOT addRelation: unlike the particle effects beside it this is a shader aura owned by ItemAuraSystem and persisted on item.data.aura, so no effect_heatmap rule is registered and addRelation would no-op silently. _(self-relation: omit target)_ |
| `effect_ink_bleed` | self-relation: fluid ink dispersion and paper-grain bleed shader on source | Fluid ink dispersion and paper-grain capillary bleed shader. Use for sketches, watercolor bleed, calligraphy and fluid dynamic art. APPLIED WITH applyEffect(item, 'ink_bleed'), NOT addRelation: owned by ItemAuraSystem and persisted on item.data.aura. _(self-relation: omit target)_ |
| `effect_liquid_metal` | self-relation: chrome-flow reflective banded shader on source | Reflective chrome-flow shader stylizes the item with banded highlights. Use for metallic logos, sci-fi aesthetic, polish. APPLIED WITH applyEffect(item, 'liquid_metal'), NOT addRelation: unlike the particle effects beside it this is a shader aura owned by ItemAuraSystem and persisted on item.data.aura, so no effect_liquid_metal rule is registered and addRelation would no-op silently. _(self-relation: omit target)_ |
| `effect_rain` | self-relation: rain particles on source | Falling raindrops cover the canvas area. Use for weather scenes, melancholy mood. _(self-relation: omit target)_ |
| `effect_rain_veil` | self-relation: falling rain streaks over source | Falling streaks: what a shutter records of rain, which is the drop's travel during the exposure rather than the drop. Use for weather, melancholy, window scenes. APPLIED WITH applyEffect(item, 'rain_veil'), NOT addRelation: owned by ItemAuraSystem and persisted on item.data.aura. _(self-relation: omit target)_ |
| `effect_ripple` | self-relation: ripple rings on source | Concentric expanding rings emanate from the item. Use for water-drop, shockwave hint, attention pulse. _(self-relation: omit target)_ |
| `effect_shockwave` | self-relation: shockwave rings on source | Single explosive ring expands outward from the item once. Use for impact moments, dramatic emphasis. _(self-relation: omit target)_ |
| `effect_smoke` | self-relation: smoke particles on source | Rising smoke trail emanates from the item. Use for damage, weight, atmosphere. _(self-relation: omit target)_ |
| `effect_snow` | self-relation: snow particles on source | Falling snowflakes drift across the canvas area. Use for winter scenes, peaceful slow motion. _(self-relation: omit target)_ |
| `effect_sparkle` | self-relation: sparkle particles on source | Twinkling particles cascade from the item. Use for celebration, magic, attention-draw moments. _(self-relation: omit target)_ |
| `effect_trail` | self-relation: motion trail on source | Particle trail follows the item as it moves. Use for motion blur, speed lines, comet tails. _(self-relation: omit target)_ |
| `effect_vortex` | self-relation: rotating condensation wall on source | A spinning wall of condensation around a hollow core — the bright band sits at the radius of maximum wind, not on the axis. Use for cyclones, portals, drains, whirlpools. APPLIED WITH applyEffect(item, 'vortex'), NOT addRelation: owned by ItemAuraSystem and persisted on item.data.aura. _(self-relation: omit target)_ |
| `exclusive_group` | mutex co-membership | Two items belong to the same exclusive group — at most one is active at a time. Activating one via setActive() deactivates siblings and pulses :enter/:exit events. |
| `expresses` | self-relation: source plays facial expression (target=null) | Source plays a named expression preset (smile, blink, surprise) driving its part_of children. Use for facial animation, character emotion. _(self-relation: omit target)_ |
| `fills_slot` | source → composition root | ANNOTATION: this item occupies slot N of a composition, by 0-based index. Together with pp:composedAs it is what lets a layout be re-run or re-targeted without re-deriving which item went where. |
| `follows` | source pursues target position | Smooth pursuit with lag — source asymptotically approaches target. Use for trailing, delay, easing motion. Contrast: attached_to is rigid (zero lag). |
| `geo_adjacent_to` | source → region | Records that the item belongs beside a geographic region, drawing the visual connection. Annotation rather than motion: it states WHERE something refers to, so a label can be re-placed without losing what it points at. |
| `geo_centers_on` | source → region | Centres and zooms the map view on a region. A camera move expressed in geographic terms rather than in canvas coordinates, which is what keeps it meaningful across projections. |
| `geo_highlights` | source → region | The item gives a map region visual emphasis — the declarative form of highlighting, so which regions are called out is part of the scene rather than a side effect of a script that ran once. |
| `geo_pinned` | source → coordinate | The item is anchored to a longitude/latitude and reprojects to the screen every frame as the globe turns, hiding on the far hemisphere. A pin that belongs to the EARTH rather than to the canvas, so it stays correct through rotation, projection changes and zoom. |
| `geo_tours` | source → route | The item tours geographic waypoints along great-circle arcs, reprojecting each frame and hiding on the far hemisphere. The map variant of pp:tours — great circles rather than straight lines, because the shortest path on a globe is not the shortest path on a screen. |
| `geo_travels_to` | source → region | The item animates along a path to a geographic destination. The route is derived from the projection, so it stays correct when the map is re-projected or re-centred. |
| `glyph_of` | source → root glyph | ANNOTATION: this character belongs to a text-effect composition, by 0-based index, pointing back at the root glyph. Membership exists ONLY on this edge — the characters are siblings, not children of a group — which is what lets the composition be selected, re-targeted or removed as one unit. |
| `group_morphs_to` | source group migrates into target group configuration | Source paper.Group's children migrate into target Group's children's positions, paired by index. Path.Line children deform via segment endpoints; other items translate. Excess children fade. Generic across any two groups. |
| `grows_from` | source scales from zero at target origin | Source scales up from zero starting at target's position. Use for spawn-from-point effects, ripple-into-being entrances. |
| `has_camera_treatment` | self-relation: annotates the item | ANNOTATION: how this composition should be FILMED — a treatment key such as a sheet reveal. Records intent for the camera rather than moving it, so the treatment survives a re-layout. _(self-relation: omit target)_ |
| `has_text_effect` | self-relation: annotates the root glyph | ANNOTATION: this glyph is the ROOT of a character-level text effect, and carries what the effect was built FROM — effect key, original content, font size, family, origin, duration and seed. That spec lives on the edge precisely so the effect can be changed or undone without retyping the text. _(self-relation: omit target)_ |
| `head_points_to` | arrow → port | An arrow's HEAD is bound to a diagram port, so the connector's end follows the item. The counterpart of pp:attachedToTail; together they are why a connector stays connected. |
| `ik_target` | source item drives IK chain on target skeleton | Target item is the end-effector goal for an IK chain on source skeleton. Use for hand-reaches-cup, foot-lock, gaze-to-target. |
| `indicates` | source pulses to highlight target | Temporary emphasis effect. mathematically: pulseScale on source triggered by target reference. |
| `inside` | source placed inside target bounds | Source is placed inside the target bounds at a 9-way anchor. Places (contrast contained_in_place, which clamps a moving item). Params: anchor, padding. |
| `is_centroid_of` | source = centroid(target, ...params.others) | Source is held at the centroid (average position) of the target and params.others (more anchor ids). |
| `is_circumcenter_of` | source = circumcenter(target, other1, other2) | Source is held at the circumcenter of the triangle target, params.other1, params.other2 (inactive when the three are collinear). |
| `is_midpoint_of` | source = midpoint(target, params.other) | Source is held at the midpoint of the target and params.other (a second anchor). Live: drag either anchor and the source follows. |
| `lies_on_line` | source = lerp(target, params.other, t) | Source is constrained to the line through the target and params.other, at fraction params.t along it (0=target, 1=other). |
| `locomotion` | source → path | Moves a skeleton root along a path while cycling poses in proportion to the distance travelled — so the feet keep up with the ground instead of sliding. Tying the gait to distance rather than to time is what removes foot-slide at any speed. |
| `maintains_distance` | source held at distance from target | Source stays at a fixed distance from target as either moves. Use for tethering, leash dynamics, fixed-spacing groups. |
| `menubar_group` | group co-membership | Two items share a menubar group — together they form a horizontal action bar (toolbar / app menu). The A11yShadowTree matcher promotes to role="menubar" + menuitem with horizontal arrow-key nav. Unlike exclusive_group, no item is "active"; clicking a menuitem fires its own on_click_fire reactions. |
| `mirrors` | source reflects target across axis | Source's transform mirrors target across an axis. Use for reflections, symmetry, mirrored character poses. |
| `morphs_to` | source shape morphs into target shape | Source's path interpolates into target's path over time. Use for shape morphing, geometry transitions. |
| `moves_along_path` | self-relation: source travels along stored path (target=null) | Item position is driven along a user-supplied path stored as params. Self-relation; named easing curves (linear / easeIn / easeOut / easeInOut / sine / bounce / pingpong). _(self-relation: omit target)_ |
| `on_click_fire` | click on source → fire target event | Source item pulses target pp:Event on click. The producer half of the event channel: it names a pp:Event rather than doing anything itself, so any number of reactions can listen to one click without the click knowing about them. |
| `on_enter_increment` | source → target | When the pointer ENTERS the item, adds N to a numeric property on the target. Edge-triggered, so it fires once on the transition rather than every frame the pointer is inside — which is the difference between a hover state and a runaway counter. |
| `on_enter_set_color` | source → target | When the pointer ENTERS the item, sets a colour on the target. Edge-triggered, so it fires once on the transition rather than every frame the pointer is inside — which is the difference between a hover state and a runaway counter. |
| `on_enter_set_data` | source → target | When the pointer ENTERS the item, writes a key into item.data on the target. Edge-triggered, so it fires once on the transition rather than every frame the pointer is inside — which is the difference between a hover state and a runaway counter. |
| `on_enter_set_property` | source activates → write item.property on target | When source becomes the active member of its exclusive_group, set target.[property] = value. |
| `on_enter_set_property_from_template` | source → target | When the pointer ENTERS the item, sets a property from a template string, interpolating stored values into it on the target. Edge-triggered, so it fires once on the transition rather than every frame the pointer is inside — which is the difference between a hover state and a runaway counter. |
| `on_enter_set_visibility` | source activates → write item.visible on target | When source activates in its group, set target.visible. The enter half of a mutex: it fires when the source BECOMES active in its exclusive group, which is what makes a tab reveal its own panel without every tab knowing about every panel. |
| `on_enter_toggle` | source → target | When the pointer ENTERS the item, flips a boolean property on the target. Edge-triggered, so it fires once on the transition rather than every frame the pointer is inside — which is the difference between a hover state and a runaway counter. |
| `on_event_add_relation` | event source → app.addRelation on target | Meta-relation — the graph modifies itself. On pp:Event pulse, app.addRelation(target, params.target, params.type, params.params). Use to attach effects, springs, or any relation in response to an event. |
| `on_event_fire_after` | event source → delayed event pulse on target | On pp:Event pulse, schedule a target pp:Event pulse N ms later. Params: { delay: ms, timeline?: "wall" \| "canvas" }. Default "wall" uses setTimeout (real-time). "canvas" schedules against app.playbackTime — pauses with timeline pause, seeks with timeline seek, loops with the canvas timeline. Use canvas mode when timing is animation-relative (state changes at t=2s of an animation); use wall mode for real-time effects (cleanup after 2 real seconds). |
| `on_event_fire_if` | event → event | On a pp:Event pulse, fire another event only if a predicate holds. The one reaction in the family that TESTS graph state instead of mutating it — its predicate is an ExpressionIR program, so the condition is data the graph can carry, not a closure it cannot. |
| `on_event_increment` | event source → numeric increment on target.data field | On pp:Event pulse, increment target.data[property] by N. Counters and steppers. Increment rather than set, so several sources can advance the same value without knowing its current one. |
| `on_event_remove_relation` | event source → app.removeRelation on target | Meta-relation — the graph modifies itself. On pp:Event pulse, app.removeRelation(target, params.target, params.type). Inverse of onEventAddRelation, used for cleanup chains. |
| `on_event_set_active` | event source → setActive on target (mutex) | On pp:Event pulse, activate target in its exclusive_group (clears siblings). |
| `on_event_set_color` | event source → write fillColor/strokeColor on target | On pp:Event pulse, set target.fillColor or .strokeColor. For selection and hover feedback. Colour is the cheapest state indicator that does not move anything, so it never disturbs layout. |
| `on_event_set_data` | event source → write item.data field on target | On pp:Event pulse, set target.data[property] = value. Writes to the item's data rather than its appearance — how a scene keeps state (a score, a mode, a flag) that other relations can then read. |
| `on_event_set_property` | event source → write item.property on target | On pp:Event pulse, set target.[property] = value. The general reaction — reach for a specific one (visibility, colour, data) where it fits, since the specific edge says what the interaction MEANS in the exported graph. |
| `on_event_set_property_from_template` | event source → derived-text write on target | On pp:Event pulse, write target.[property] with a template-interpolated string. `template` contains `{key}` tokens; each is replaced with the stringified value of target.data[key] (default) or target[key] (when `source: "item"`). Missing keys resolve to "". Pairs with on_event_increment / on_event_set_data on the same channel to drive counters, formatted readouts, status lines, and debug HUDs — anything where the target text is derived from runtime state. Params: { property, template, source?: "data" \| "item" }. |
| `on_event_set_visibility` | event source → write item.visible on target | On pp:Event pulse, set target.visible. The show/hide half of every tab, accordion and disclosure; pair with pp:exclusiveGroup when only one panel may be open. |
| `on_event_store_increment` | event → store | On a pp:Event pulse, add N to a stored numeric key, creating it at 0 if absent. Increment rather than set, so several sources can advance one score without any of them knowing its current value. |
| `on_event_store_set` | event → store | On a pp:Event pulse, write `key = value` into a pp:Store. The persistent counterpart of pp:onEventSetData, which only reaches item.data and dies with the page. |
| `on_event_toggle` | event source → boolean flip on target | On pp:Event pulse, flip target.visible or target.data[property]. |
| `on_exit_increment` | source → target | When the pointer LEAVES it, adds N to a numeric property on the target. Edge-triggered, so it fires once on the transition rather than every frame the pointer is inside — which is the difference between a hover state and a runaway counter. |
| `on_exit_set_color` | source → target | When the pointer LEAVES it, sets a colour on the target. Edge-triggered, so it fires once on the transition rather than every frame the pointer is inside — which is the difference between a hover state and a runaway counter. |
| `on_exit_set_data` | source → target | When the pointer LEAVES it, writes a key into item.data on the target. Edge-triggered, so it fires once on the transition rather than every frame the pointer is inside — which is the difference between a hover state and a runaway counter. |
| `on_exit_set_property` | source deactivates → write item.property on target | When source stops being the active member of its exclusive_group, set target.[property] = value. |
| `on_exit_set_property_from_template` | source → target | When the pointer LEAVES it, sets a property from a template string, interpolating stored values into it on the target. Edge-triggered, so it fires once on the transition rather than every frame the pointer is inside — which is the difference between a hover state and a runaway counter. |
| `on_exit_set_visibility` | source deactivates → write item.visible on target | When source deactivates in its group, set target.visible. The exit half, firing as the source LOSES active status — what hides the outgoing panel. Without it a tab set reveals panels and never hides them. |
| `on_exit_toggle` | source → target | When the pointer LEAVES it, flips a boolean property on the target. Edge-triggered, so it fires once on the transition rather than every frame the pointer is inside — which is the difference between a hover state and a runaway counter. |
| `on_key_fire` | keydown on source → fire target event | Source pulses target pp:Event when a key matches and the source has focus (or globally if params.global). Params: { key, modifiers?, global?, preventDefault? }. WCAG 2.2 keyboard-operability primitive. |
| `on_pointer_enter_fire` | pointer enter on source → fire target event | Source pulses target pp:Event when pointer enters its bounds. |
| `on_pointer_exit_fire` | pointer leave on source → fire target event | Source pulses target pp:Event when pointer leaves its bounds. |
| `on_top_of` | source placed on top of target | Source bottom edge sits on target top edge. Use for stacking (a cocktail on a bar). Params: gap, align (left/center/right), overhang. |
| `orbits` | source orbits target | Source revolves around target at a fixed radius. Use for celestial mechanics, satellites, rotating-around-X relationships. Spatial params (radius) accept canvas-relative units (e.g. '30vmin' = 30% of min(canvasW,canvasH)) so the scene adapts to any size/aspect. |
| `parallax` | source depth-shifts relative to target scroll | Source moves at a depth-scaled fraction of target's motion. Use for background layers, parallax scrolling, depth illusion. |
| `part_of` | source is named part of target — follows target position with named role metadata | Source is a named sub-element of target (e.g. eye_left part_of face). Use for compound items and named sub-element addressing. |
| `part_of_figure` | source part → figure root | ANNOTATION: this drawn part belongs to a directed figure, with the role it plays. Membership exists ONLY on this edge, exactly as it does for pp:glyphOf — the parts are siblings, not children of a group, which is what lets a figure be selected, recoloured or removed as one while each part keeps its own keyframe track. Deliberately NOT pp:partOf: that edge cascades the parent's POSITION onto the child, and a figure composed by the character layer already carries a carried part's motion inside its own track, so the two together would move every carried part twice. |
| `points_at` | source rotates to face target | Source rotates to always face target. Use for compass needles, gun turrets, gaze direction, arrows tracking a target. |
| `pose_layer` | self-relation: annotates the skeleton | Adds a bone-masked pose animation layer to a skeleton, so a wave can play on one arm while a walk runs underneath. The mask is what makes layers compose instead of overwrite. _(self-relation: omit target)_ |
| `repels` | source → target | The source moves away from the target when it comes within a repulsion radius, and eases back to where it was when the target leaves. Params: force, maxDistance, minDistance, returnSpeed. Use for crowd avoidance and for things that should react to a cursor without being dragged by it. |
| `restores_from` | item → store | At LOAD, once, before the first frame, set a property on this item from a stored key — with a fallback when the key is absent. The read half of persistence: without it a store is write-only and continuity across sessions, the entire point, does not exist. |
| `spring_follow` | source → target | Source follows target with spring dynamics — it lags behind, overshoots and settles rather than tracking rigidly. Params: stiffness (0-1), damping (0-1, higher settles sooner), mass, maxDisplacement in pixels. Use for secondary motion: hair, tails, cloth, anything that should feel attached rather than welded. |
| `staggered_with` | source staggers after target (index-ordered) | Stored as pairwise edges with index param to reconstruct group ordering. Conceptually 1→N but decomposed into binary pairs. |
| `synced_to_audio` | self-relation: annotates the item | ANNOTATION: this composition is timed to an audio track, carrying the source asset, the detected bpm and the onset times in seconds. The beats live on the EDGE so they survive save/restore and can be queried, rather than in a local variable. _(self-relation: omit target)_ |
| `syncs_with` | source → target | The source's animation runs on the target's timeline, with a time offset and a speed ratio. What makes two items share a clock rather than merely start together — they stay in step even when the target's timing changes. |
| `time_expression` | self-relation: expression on source (target=null) | Source property evaluates a math expression of time each frame. Use for custom oscillations, formula-driven motion. _(self-relation: omit target)_ |
| `tours` | source → route | The item visits a route of waypoints — dwelling at each, moving between them, optionally turning to face the direction of travel. The canvas-general form; pp:geoTours is its globe-aware counterpart. |
| `triggers_animation` | source → target | Source starts the target's animation when a condition is met — on complete, on start, at a time, or on each loop, with an optional delay. The declarative form of "and then": it puts sequencing in the graph instead of in a callback nobody can query. |
| `unknown` | unspecified | Relation type not expressible in current vocabulary. Enables vocabulary gap discovery — count and inspect unknown relations to identify missing edge types. |
| `wave_through` | source receives wave from target (phase-ordered) | Stored as pairwise edges with index param for phase offset. Conceptually 1→N but decomposed into binary pairs. |
| `wiggle` | self-relation: noise on source (target=null) | Source position / rotation jitters via noise-driven offset. Use for hand-drawn liveliness, idle motion, organic shake. _(self-relation: omit target)_ |

## Generators (72) — backgrounds & generative content

Run with `pinepaper_execute_generator { generator: "<name>", colors, bgColor }`
(or `app.executeGenerator("<name>", {…})`). Use for backgrounds, textures, patterns,
particle fields, and math/scene art — not for foreground objects.

| generator | what it draws |
|-----------|---------------|
| `draw3DParametricCurve` | Plots a 3D parametric curve (x(t), y(t), z(t)) projected to the canvas with rotation + perspective. Use for helices, knots, spherical spirals, space-curve math art. |
| `draw3DSurface` | Parametric 3D surface with perspective projection (Klein bottle, Möbius strip, torus). Use for math art, geometry visualization. |
| `draw3DWorld` | 3 d world background generator — procedural "3 d world" backdrop. |
| `drawBlobs` | Soft organic blob shapes (smoothed paths through a jittered circle), colored from an OKLCH palette. Use for playful backgrounds, sticker shapes, lava/bubble motifs. |
| `drawBokeh` | Soft circular out-of-focus light dots. Use for photographic bokeh, romantic blur, ambient highlights. |
| `drawCharacterEyes` | character eyes background generator — procedural "character eyes" backdrop. |
| `drawChoroplethMap` | choropleth map background generator — procedural "choropleth map" backdrop. |
| `drawCircuit` | Maze-like circuit-board pattern with nodes and traces. Use for tech backdrops, sci-fi panels. |
| `drawConcentricRings` | Expanding concentric ring patterns. Use for ripple, radar, target, hypnotic, meditative designs. |
| `drawConstellation` | constellation background generator — procedural "constellation" backdrop. |
| `drawCornerAccents` | Decorative corner flourishes framing the canvas. Use for certificates, invitations, formal designs, polished frames. |
| `drawCosmosSpace` | cosmos space background generator — procedural "cosmos space" backdrop. |
| `drawCountryMap` | country map background generator — procedural "country map" backdrop. |
| `drawDayNightCycle` | day night cycle background generator — procedural "day night cycle" backdrop. |
| `drawFallingPetals` | Gentle falling petals drifting downward with wind sway. Use for spring, romantic, celebration, wedding, birthday designs. |
| `drawFibonacci` | fibonacci background generator — procedural "fibonacci" backdrop. |
| `drawFireflies` | Glowing firefly dots drifting in organic patterns. Use for magical, night, forest, warm summer evening moods. |
| `drawFloatingLeaves` | Leaves drifting on wind currents with gentle rotation. Use for autumn, nature, organic, calming backgrounds. |
| `drawFlowCurves` | Elegant flowing curve lines across the canvas. Use for luxury, fashion, minimal, sophisticated backgrounds. |
| `drawFlowField` | flow field background generator — procedural "flow field" backdrop. |
| `drawFluidFlow` | Curving streamlines suggesting fluid motion. Use for water / wind / lava illustration, organic backdrops. |
| `drawFormulaArt` | formula art background generator — procedural "formula art" backdrop. |
| `drawFunctionPlot` | Plots a math expression y=f(x) over an x-range. Use for math illustrations, function visualization, education. |
| `drawGeometricAbstract` | Randomized composition of overlapping geometric shapes. Use for abstract art, modern poster backdrops. |
| `drawGlobeWireframe` | globe wireframe background generator — procedural "globe wireframe" backdrop. |
| `drawGlowOrbs` | Soft glowing orbs drifting slowly. Use for magical, dreamy, ethereal, ambient backgrounds. |
| `drawGoldenSpiral` | golden spiral background generator — procedural "golden spiral" backdrop. |
| `drawGPUCaustics` | Underwater caustic light patterns — Voronoi-based with deep blue to cyan palette. Use for underwater, pool, ocean-floor scenes. GPU-accelerated. |
| `drawGPUClouds` | Volumetric FBM cloud field with warm edge lighting and sky gradient. Use for sky, atmosphere, dreamy backgrounds. GPU-accelerated. |
| `drawGPUOcean` | Multi-layer sine waves with specular sun highlights and depth coloring. Use for ocean, sea, water backgrounds. GPU-accelerated. |
| `drawGPUPlasma` | Immersive fractal plasma — FBM noise + domain warp + animated cosine palette. Use for organic, fluid, trippy backgrounds. GPU-accelerated. |
| `drawGPUStarfield` | Multi-layer parallax starfield with twinkling stars. Use for space, night sky, sci-fi backgrounds. GPU-accelerated. |
| `drawGPUTunnel` | Rotating checkered tunnel with depth fog in warm tones. Use for portal, vortex, hypnotic, retro sci-fi backgrounds. GPU-accelerated. |
| `drawGPUVoronoi` | Animated Voronoi tessellation with glow edges. Use for cellular, organic, abstract tech backgrounds. GPU-accelerated. |
| `drawGradientMesh` | Smooth multi-color noise gradient. Use for atmospheric backdrops, mood lighting. |
| `drawGrid` | Uniform grid pattern. Use for blueprint backgrounds, technical aesthetics, layout reference. |
| `drawHalftone` | Grid of dots whose radius rides a tone field (noise / radial / linear) with color from an OKLCH palette. Use for print-halftone looks, soft textured backgrounds, retro pop art. |
| `drawKaleidoscope` | kaleidoscope background generator — procedural "kaleidoscope" backdrop. |
| `drawLowPoly` | Triangulated low-poly background — a jittered vertex grid split into triangles, each facet flat-filled from an OKLCH gradient. Use for modern geometric backdrops, crystalline textures. |
| `drawMetaballs` | metaballs background generator — procedural "metaballs" backdrop. |
| `drawNeonGrid` | neon grid background generator — procedural "neon grid" backdrop. |
| `drawNoiseTexture` | Static or animated noise texture. Use for grain overlays, paper textures, depth-cueing backgrounds. |
| `drawOrganicFlow` | Flowing curves that breathe and shift over time. Use for living abstract backgrounds, mood ambience. |
| `drawParametricCollection` | parametric collection background generator — procedural "parametric collection" backdrop. |
| `drawParametricCurve` | Plots a parametric (x(t), y(t)) curve over a t-range. Use for Lissajous figures, spirals, parametric art. |
| `drawPattern` | Tileable geometric pattern (chevrons, hexagons, polkadots). Use for textured backgrounds, brand backdrops. |
| `drawPeaks` | Stacked zig-zag mountain/ridgeline bands closed to the canvas bottom with an OKLCH palette ramp. Use for layered-mountain backdrops, ridge silhouettes, outdoor scenes. |
| `drawPerspectiveGrid` | perspective grid background generator — procedural "perspective grid" backdrop. |
| `drawPoissonDisk` | poisson disk background generator — procedural "poisson disk" backdrop. |
| `drawPoissonShapesAsync` | poisson shapes async background generator — procedural "poisson shapes async" backdrop. |
| `drawRibbons` | Smooth Bézier ribbons undulating across a shared Perlin noise field, colored from an OKLCH palette. Use for flowing aurora / silk / current backdrops, organic motion. |
| `drawRiggedCharacter` | rigged character background generator — procedural "rigged character" backdrop. |
| `drawScatter` | A scattered field of small shapes (circles / triangles / squares) sized and colored from an OKLCH palette. Use for confetti, starfields, particle textures, decorative speckle. |
| `drawShaderArt` | shader art background generator — procedural "shader art" backdrop. |
| `drawSimulation` | Renders a live ODE-based dynamic system (pendulum, Lorenz, spring-mass). Use for physics demos, chaos, science visuals. |
| `drawSolarSystem` | solar system background generator — procedural "solar system" backdrop. |
| `drawSpectrumAnalyzer` | Renders a signal's frequency spectrum via FFT. Use for audio visualizers, signal-processing demos, abstract data motion. |
| `drawStackedCircles` | Vertical stack of overlapping circles. Use for snowman-shapes, decorative beadwork, abstract sculpture forms. |
| `drawStackedWaves` | Layered filled cubic-Bézier wave bands stacked at increasing baselines with an OKLCH palette ramp. Use for hero backgrounds, section dividers, ocean/dune/hill backdrops. |
| `drawStarfield` | starfield background generator — procedural "starfield" backdrop. |
| `drawSunburst` | Radial rays emanating from a center point. Use for solar emblems, celebratory backgrounds, retro motifs. |
| `drawSunburstLines` | sunburst lines background generator — procedural "sunburst lines" backdrop. |
| `drawSunsetScene` | Layered horizon scene with sky-color gradient. Use for landscape backdrops, mood-setting backgrounds. |
| `drawTadpoles` | tadpoles background generator — procedural "tadpoles" backdrop. |
| `drawTessellation` | tessellation background generator — procedural "tessellation" backdrop. |
| `drawTruchet` | Seeded Truchet tiling of quarter-arc or diagonal tiles, colored from an OKLCH palette. Use for flowing maze textures, generative line art, circuit-like backdrops. |
| `drawUSAMap` | usa map background generator — procedural "usa map" backdrop. |
| `drawVoronoi` | voronoi background generator — procedural "voronoi" backdrop. |
| `drawWaves` | Layered horizontal sine waves. Use for water surfaces, audio waveforms, ocean backgrounds. |
| `drawWindField` | Flow-field of streaming particles driven by Perlin noise. Use for wind visualization, smoke trails, atmospheric motion. |
| `drawWorldMap` | world map background generator — procedural "world map" backdrop. |
| `drawYeganehMountains` | yeganeh mountains background generator — procedural "yeganeh mountains" backdrop. |

## Simple animations (8)

Set on creation (`create_item { animationType: "<name>" }`) or via `app.animate(item,
{ animationType: "<name>" })`. These are the always-available primitives; a larger
Animate.css-parity preset library (~100 entrances/exits/attention-seekers) is also
available by preset name.

| animationType | motion |
|---------------|--------|
| `pulse` | rhythmic scale in/out — heartbeat, breathing, “live” emphasis |
| `rotate` | continuous spin around the item center |
| `bounce` | vertical ease up-and-down |
| `fade` | opacity oscillation in/out |
| `wobble` | playful side-to-side rotation |
| `shake` | rapid horizontal jitter — error/alert |
| `swing` | pendulum rotation from the top |
| `jelly` | squash-and-stretch wobble |

## Motion (18) — how a rig moves

A pose is a snapshot; a **motion** is a function of scene time. Drive all of
these through `pinepaper_rigging { action }` (or `app.riggingSystem.<method>`).

The shape of the work: save or load POSES, sequence them into a CLIP, join clips
into a performance, and run a LOCOMOTION track underneath so the figure travels.
A rig you did not build needs `list_bones` first — an inline pose is
`{ boneId: angleDeg }` and nothing else returns a bone id — and a fresh rig has no
poses at all until `load_pose_library` gives it some.

| concept | engine | what it is |
|---------|--------|------------|
| `PoseSequence` | `playPoseSequence` | Keyed poses over scene time, each naming a saved pose or an inline bone-angle map. Sampled as a pure function of playbackTime, so it scrubs, pauses and bakes. ONE per skeleton: starting another replaces it, which is why joining clips is a planning problem rather than a second playback slot. |
| `MotionClip` | `stitchPoses` | One bounded span of motion offered for joining — a walk cycle, a jump, a held idle. Carries how it joins as well as what it plays: whether it is cyclic (and so can be entered at any phase), how many times it repeats, and how long its seam should be. |
| `MotionSeam` | `stitchPoses` | The join between two clips: an overlap in which both are sampled and cross-faded per bone. Reports the angular mismatch it could NOT remove, in degrees — near zero is a real match, a large number means the blend is hiding a cut. That figure is the difference between a transition and an edit, and it is measurable rather than a matter of taste. |
| `PoseBlend` | `interpolatePoses` | A pose part way between two others, interpolated per bone along the SHORTEST arc. Going the long way round turns a 20° step across ±180 into a 340° swing, which reads as a limb rotating backwards rather than as a blend. |
| `PoseLayer` | `addPoseLayer` | An additive motion layer over whatever pose is current, cycling its own pose list on its own clock. Layers compose, which is what lets a breath run underneath a walk instead of replacing it. |
| `GaitCycle` | `autoWalk` | A looping limb pattern — the walk or run cycle itself, as a set of named poses (walk_00…, walk_contact_L, walk_passing_L) rather than a formula. Because it is a cycle, it can be entered at any phase, which is what makes joining it to another motion tractable. |
| `LocomotionTrack` | `moveRoot` | Root translation across the world over SCENE SECONDS — what makes a figure travel rather than march on the spot. Sampled deterministically rather than integrated per frame, so it scrubs and exports; keyed on the same clock as the pose sequence, so a track shorter than the performance lands the figure early and leaves it standing. |
| `SecondaryMotion` | `addSecondaryMotion` | Spring-driven follow-through on a chain of bones — a tail, hair, cloth — that lags the motion driving it. Not decoration: the lag is what makes a rig read as having mass rather than as a diagram of one. |
| `BakedAnimation` | `bakeAnimation` | A rig sampled frame by frame into plain item keyframes, so motion that only a skeleton could produce survives into formats that have no concept of one. Writes onto the ATTACHED items — a skeleton with nothing bound to it bakes to nothing. |
| `MotionCapture` | `applyExternalPose` | Recorded motion driving a rig — a BVH clip, a Spine export, or live landmarks from a camera. Retargeting maps it by bone NAME, so the names are the contract; root translation is kept as a separate track rather than baked into the poses, because a walk whose root motion was dropped is a march on the spot. |

### Procedural layers (4) — one call, keeps running

| layer | engine | what it is |
|-------|--------|------------|
| `walk` | `autoWalk` | A walk cycle played from saved walk poses. A pose PLAYER, not a generator: it needs at least two poses named walk_00… or walk_contact_L…, which is exactly what the humanoid and quadruped libraries save. |
| `idle` | `autoIdle` | A small continuous shift so a character at rest is not a still image. Finds its bones by NAME — head, hip, upper_hub, spine — and declines on a rig that uses others. |
| `breath` | `autoBreath` | A slow rise and fall through the spine. Finds spine, chest, upper_spine or body by name, and is the cheapest single thing that makes a rig look alive. |
| `jump` | `autoJump` | A parabolic root arc with an impact compression at the landing, cleaning itself up afterwards. Combines a pose layer with root physics, which is why it reads as weight rather than as a translation. |

### Expressions (4) — faces, no skeleton required

Driven through `part_of` ROLE tokens (eye_left, pupil_left, mouth, brow_right…),
so any character whose parts carry those roles can use them. Wire with
`add_relation { relation: "expresses" }`.

| expression | what it does |
|------------|--------------|
| `blink` | Eyes close and reopen, periodically. Scales the eye_* roles and hides the pupil_* ones — which is why an imported layer set maps its iris to pupil rather than to a pupil-shaped name. |
| `smile` | The mouth role curves upward and the eyes narrow slightly. Sustained rather than periodic. |
| `frown` | The mouth role curves down and the brows draw in. Sustained. |
| `surprise` | Eyes widen and the mouth opens. Sustained, and the one preset where the eye roles grow rather than shrink. |

## Design taxonomy — three axes, chosen independently

A **register** is which design language a composition speaks, a **level** is how
well that language is executed, and a **medium** is what physically makes the
marks. They are independent on purpose: an embroidered schematic is a technical
register at a refined level in a thread medium, and no single better/worse ranking
can express that. Naive at its best is a real thing, not a failed attempt at
editorial — so pick a register, do not climb toward one.

Resolve craft values with `app.resolveDesignRegister("<register>", <level>)`.

### Registers (5) — which design language

| register | what it is |
|----------|------------|
| `naive` | Flat colour, even spacing, symmetric placement, decoration welcome. The register of a nursery poster or a picture book. Also where undirected output lands by default, which is why naming it matters: it is a legitimate idiom, not a bug, and calling it by name separates "chose this" from "chose nothing". |
| `playful` | Rounded forms, a warm limited palette, bouncy motion. Restrained enough to read as designed, loose enough to stay friendly. |
| `poster` | One dominant hue and enormous type contrast, readable across a room. Scale does the work, so the type-scale ratio is the highest of any register. |
| `editorial` | Ink plus one or two hues, a modular type scale, hairline rules, asymmetric balance, and negative space treated as a subject rather than as leftover. Motion only where it carries meaning. |
| `technical` | Monochrome with a single accent, a tight grid, monospace labels, no ornament at all. A diagram, not a picture. |

### Craft levels (4) — how well, WITHIN a register

Climbing a level never widens a budget: restraint is the direction of craft.

| level | name | what changes |
|-------|------|--------------|
| **1** | Sketch | Level 1. Defaults accepted: no optical correction, no considered type scale, budgets untightened. |
| **2** | Competent | Level 2. One consistent type scale and one grid, held throughout the composition. |
| **3** | Refined | Level 3. Optical alignment rather than merely mathematical, a tightened palette, and whitespace placed deliberately. |
| **4** | Art directed | Level 4. A concept drives every choice and exactly one rule is broken on purpose. Meaningless below this level, where the rules are not yet kept reliably enough for a break to read as intent rather than error. |

### Media (9) — what makes the marks

Every medium declares how faithfully a VECTOR engine can render it, because
naming a medium does not create its marks. **native** = the characteristic marks
ARE vector geometry; **stylised** = a recognisable impression, and the limitation
is stated in the description; **absent** = registered so a request for it is
REFUSED with a reason rather than quietly producing flat shapes in its colours.
Check with `app.resolveDesignMedium("<medium>")` before promising one.

| medium | fidelity | makes marks with | what it is |
|--------|----------|------------------|------------|
| `vector` | native | — | Flat fills, clean edges, uniform strokes. The engine's own idiom and a real medium in its own right — screen-print and modern flat illustration live here. |
| `thread` | native | `ThreadPainting` | Needlepainting: rows of directional stitches that follow the form, so a feather or a petal reads as volume rather than as fill. Native because a stitch IS vector geometry — a short oriented segment with a taper and a sheen — which makes a vector engine genuinely better at this medium than a raster painting engine. |
| `ink` | native | `VectorBrush` | Pen and brush marks with pressure-varying width and hard edges. Native: the existing brush profiles already make these marks, so no new geometry is required. |
| `watercolor` | native | `WatercolorBrush` | Layered translucent washes whose edges feather and pool instead of ending. Native: a wash is real vector geometry — overlapping low-opacity organic deposits with a fainter capillary edge pool — and the wet bleed is a vertex diffusion on that geometry, so a stroke stays editable and export-lossless. |
| `hatch` | native | `Hatching` | Value stated as line density rather than as colour: ruled lines, closer together where it is darker. Pen-and-ink, engraving, and every drawing made with one nib. Native in the strongest sense — a line IS vector geometry, so this is the medium itself and not a picture of it, and it is the only medium here that survives being drawn by a plotter. |
| `cutPaper` | native | `CutoutStylePresets` | Flat shapes with a cut edge and a cast shadow, layered. Native: a vector silhouette with an offset shadow is the medium rather than an approximation of it. |
| `charcoal` | stylised | `VectorBrushMaterial` | Granular tooth and smudged edge. Stylised: the grain is a shader over a silhouette, not deposited pigment — there is no smudging, no lifting and no true tonal blending. |
| `oil` | stylised | `VectorBrush` | Impasto volume, glazing, wet-in-wet blending, softened edges. Stylised: the signature is subsurface and continuous-tone, and impasto relief, glaze translucency and blended edges are pigment behaviour rather than geometry. The engine can suggest brush-shaped marks and a loaded palette; it cannot produce the medium. |
| `encaustic` | absent | — | Pigmented wax fused with heat: translucent depth built in layers, with edges that flow rather than end. Absent, and registered precisely so it can be refused with that reason — volumetric layered translucency has no vertex-level expression, and a flat approximation would misrepresent the medium rather than approximate it. |

### Stitches (4) — the marks of the thread medium

Render an item in thread with `app.applyThreadPainting(item, { stitch, field, stitchLen, width })`,
passing one of the names below as `stitch` (default `longAndShort`). An unknown
name is REFUSED rather than defaulted, and re-stitching an item replaces its
previous stitching instead of stacking a second copy on it.
The direction field is what makes it needlepainting rather than hatching:
`{ kind: "radial", cx, cy }` for anything that radiates, `{ kind: "spine", spine: [...] }`
to run stitches along a midrib or feather shaft, `{ kind: "constant", angle }` for flat hatch.

| stitch | what it is |
|--------|------------|
| `satin` | Parallel stitches spanning edge to edge, filling a narrow shape in one flat sheet. The stitch that gives a petal or a letter its sheen, because every thread lies the same way and catches light together. |
| `longAndShort` | Satin worked in staggered lengths so successive rows interlock instead of banding. The stitch that makes needlepainting shade continuously — the variance in stitch length IS the blend. |
| `seed` | Short stitches scattered at many angles. Texture rather than direction — used to break up a flat area or to suggest granularity without describing form. |
| `stem` | Overlapping slanted stitches following a line, making a rope-like outline. The stitch for stems, contours and any edge that should read as drawn rather than cut. |

## Path geometry (14 edit kinds) — the vertex level

Every shape here is a list of anchors, each carrying two Bezier handles stored
RELATIVE to their own anchor. That is the level at which a drawn line and a
generated one become the same kind of thing, and it is what `app.modify(item,
{ segments })` and `app.create('path', { segments })` both read and write.

`app.getPathGeometry(item)` returns that geometry normalized: anchors relative
to `item.position`, with the item's matrix already applied. This matters more
than it sounds — items live in two regimes here (transform baked into the
segments, or held in a matrix), and raw segments from the two are entirely
different numbers for the same picture. Read the normalized form, not `item.segments`.

Name an edit by its INTENT with `app.recordSegmentEdit(item, { kind, indices,
before, after })`. The kinds below are the ones with names; the set is OPEN, and
a kind nobody has named yet is recorded and flagged rather than refused — if you
are doing something these do not describe, say what it is and it will be kept.
The log is what turns a session of drawing into training data: "mirrored this
join" is learnable, and the pair of coordinates it produced is not.

| kind | what it does |
|------|--------------|
| `moveAnchor` | Move the anchor point. The curve translates around it because both handles are stored relative to the anchor — the edit that repositions a vertex without restyling the curve through it. |
| `moveHandle` | Move one handle freely — the general case, when neither a pure rotation nor a pure change of tension describes what was wanted. Recorded when the more specific kinds do not apply, so it is the honest fallback rather than the default. |
| `rotateHandles` | Turn the handle pair about its anchor, keeping both lengths. Changes which way the curve passes through the point without changing how hard it pulls — the edit that swings a stroke while preserving its weight. |
| `scaleHandle` | Lengthen or shorten a handle along its own direction. Direction is held, so the curve keeps its heading and only its tension changes — flatter as the handle shortens, fuller as it grows. |
| `mirrorHandles` | Make the two handles opposite and equal, so the curve passes through the point with no change of direction or of tension. The strictest smooth join, and the one that survives later edits to either side. |
| `alignHandles` | Make the handles collinear while each keeps its own length. Smooth in direction but asymmetric in tension — how a curve eases out of a tight turn into a long sweep. |
| `breakHandles` | Release the collinearity so the two sides move independently, turning a smooth point into a corner. The inverse of aligning, and what makes a hard join intentional rather than an artefact of imprecise dragging. |
| `retractHandle` | Collapse a handle to zero, making the span beside it a straight line. Distinct from shortening it a long way: at exactly zero the curve IS a line, which is a statement about the shape rather than a very flat curve. |
| `copyHandles` | Apply one segment's handle configuration to another. How a repeated form — a row of petals, the shoulders of a letter — is made consistent by hand, and the edit that most directly states 'these two points are the same kind of point'. |
| `insertSegment` | Add a vertex on an existing span. Splitting at a parameter reproduces the original curve exactly, so the shape is unchanged and only its editability increases — the point of the operation. |
| `removeSegment` | Delete a vertex. Unlike inserting one this DOES change the shape — the span between the surviving neighbours is refitted — which is why the two are not inverses and why a removal is worth recording separately. |
| `replaceGeometry` | Replace the whole segment list at once. What an import, a morph target or a programmatic rewrite performs, as against a hand edit to one vertex — recorded distinctly so a corpus can tell an artist's decision from a bulk substitution. |
| `smoothPath` | Recompute handles across a run of segments for continuity, leaving the anchors where they are. Says "make this flow" about a shape whose points are already right. |
| `simplifyPath` | Fit the same curve with fewer segments, within a tolerance. The counterpart to smoothing: smoothing keeps the points and changes the curve, simplifying keeps the curve and drops points. |

## Shader nodes (15) — what an effect is MADE of

GLSL primitives in `js/gpu/AuraNoiseGLSL.js`, as graph citizens. `built from`
is the composition edge: follow it to see a program decompose into terms, or
run it backwards to build one that does not exist yet. These are WebGL2 GLSL —
there is no WGSL port, and the WebGPU programs inline their own noise.

| node | role | signature | built from |
|------|------|-----------|------------|
| `ppHash11` | hash | `float ppHash11(float p)` | — |
| `ppHash12` | hash | `float ppHash12(vec2 p)` | — |
| `ppHash13` | hash | `float ppHash13(vec3 p3)` | — |
| `ppHash22` | hash | `vec2 ppHash22(vec2 p)` | — |
| `ppHash33` | hash | `vec3 ppHash33(vec3 p3)` | — |
| `ppVNoise2` | noise | `float ppVNoise2(vec2 x)` | `ppHash12` |
| `ppFbm2` | fractal | `float ppFbm2(vec2 p, int octaves)` | `ppVNoise2` |
| `ppTileHash33` | hash | `vec3 ppTileHash33(vec3 p, float period)` | `ppHash33` |
| `ppPerlin3Tiled` | noise | `float ppPerlin3Tiled(vec3 x, float period)` | `ppTileHash33` |
| `ppPerlinFbm3` | fractal | `float ppPerlinFbm3(vec3 p, float period, int octaves)` | `ppPerlin3Tiled` |
| `ppWorley2` | cellular | `float ppWorley2(vec2 p, float cells)` | `ppHash22` |
| `ppWorleyFbm2` | fractal | `float ppWorleyFbm2(vec2 p, float cells)` | `ppWorley2` |
| `ppIgn` | dither | `float ppIgn(vec2 p)` | — |
| `ppHenyeyGreenstein` | scattering | `float ppHenyeyGreenstein(float cosT, float g)` | — |
| `ppSchlick` | scattering | `float ppSchlick(float cosTheta, float f0)` | — |

Built-in effects and the nodes they compose:

- `electricArc` — `ppPerlin3Tiled` + `ppPerlinFbm3` + `ppHash11`
- `vortex` — `ppPerlinFbm3` + `ppHenyeyGreenstein`
- `rainVeil` — `ppHash11` + `ppIgn`
- `caustics` — `ppWorleyFbm2` + `ppWorley2` + `ppSchlick`

The remaining built-in auras predate the shared module and inline their own
noise, so they compose from nothing here — that is a real gap, not an omission.

## The maths (66)

What each of these actually computes, taken from the implementation rather than
described around it. Use them to reason about what a parameter will DO — whether
a change is linear or eased, what a residual of 26 means next to one of 0.02, why
a seam has a width at all. Angles are DEGREES; time is SECONDS on the scene clock.
The shader-node formulas are the ONE exception: they are GLSL, where angles are
RADIANS and the inputs are normalised coordinates, not scene units.

**`ppHash11`**

```
p = fract(p * 0.1031);  p *= p + 33.33;  p *= p + p;  return fract(p)
```

**`ppHash12`**

```
p3 = fract(p.xyx * 0.1031);  p3 += dot(p3, p3.yzx + 33.33);  return fract((p3.x + p3.y) * p3.z)
```

**`ppHash13`**

```
p3 = fract(p3 * 0.1031);  p3 += dot(p3, p3.zyx + 31.32);  return fract((p3.x + p3.y) * p3.z)
```

**`ppHash22`**

```
p3 = fract(p.xyx * vec3(0.1031, 0.1030, 0.0973));  p3 += dot(p3, p3.yzx + 33.33);  return fract((p3.xx + p3.yz) * p3.zy)
```

**`ppHash33`**

```
p3 = fract(p3 * vec3(0.1031, 0.1030, 0.0973));  p3 += dot(p3, p3.yxz + 33.33);  return fract((p3.xxy + p3.yxx) * p3.zyx)
```

**`ppVNoise2`**

```
u = f*f*(3 - 2f)  (smoothstep);  bilinear mix of ppHash12 at the four lattice corners of floor(x)
```

**`ppFbm2`**

```
v = SUM over i<octaves of a*ppVNoise2(p),  with p *= 2 and a *= 0.5 each octave, a0 = 0.5;  loop bounded at 8
```

**`ppTileHash33`**

```
normalize(ppHash33(mod(p, period)) * 2 - 1)
```

**`ppPerlin3Tiled`**

```
u = f*f*f*(f*(6f - 15) + 10)  (quintic);  n = SUM over the 8 corners o of w(o) * dot(g(i+o), f - o),  g = ppTileHash33, w = trilinear weight
```

**`ppPerlinFbm3`**

```
f = SUM over i<octaves of amp*ppPerlin3Tiled(p, per),  with p *= 2, per *= 2, amp *= 0.5 each octave, amp0 = 0.5
```

**`ppWorley2`**

```
p *= cells;  minDist = MIN over the 3x3 neighbour cells o of |o + ppHash22(mod(i+o, cells)) - f|^2;  return clamp(sqrt(minDist), 0, 1)
```

**`ppWorleyFbm2`**

```
0.625*ppWorley2(p, cells) + 0.25*ppWorley2(p, 2*cells) + 0.125*ppWorley2(p, 4*cells)
```

**`ppIgn`**

```
fract(52.9829189 * fract(dot(p, vec2(0.06711056, 0.00583715))))
```

**`ppHenyeyGreenstein`**

```
(1 - g^2) / (4*pi * (1 + g^2 - 2*g*cos(theta))^1.5),  with the denominator floored at 1e-4 before the power
```

**`ppSchlick`**

```
f0 + (1 - f0) * (clamp(1 - cos(theta), 0, 1))^5
```

**`timeExpression`**

```
value = f(t, v),  t = scene time in seconds, v = baseValue;  signal mode parses f into the Expression IR and evaluates it as a pure function of t
```

The formula travels INSIDE the scene document as relation params, which is why a shared motion preset is an instance of this relation rather than a new relation type: a scene built from one plays back with no catalogue and no network.

**`Flip`**

```
track_i = [ {t: delay_i, props: first_i}, {t: delay_i + duration, props: last_i} ] for every property where |last - first| > epsilon
```

Invert needs no step of its own: PinePaper keyframes are ABSOLUTE, so a track that starts at First already puts the item back. Rotation is compared on the SHORTEST ARC — 359 to 1 is two degrees, and comparing them as plain numbers spins the item almost all the way round the wrong way.

**`TimeScale`**

```
playbackTime = (now - startTime) * rate;  on a rate change, startTime <- now - playbackTime / rate
```

A looped reverse must wrap with ((t mod d) + d) mod d — JavaScript's % keeps the sign of the dividend, so a negative time would clamp every track to its first frame and the scene would look frozen rather than reversed.

**`InputDrivenPlayback`**

```
progress = clamp01(startOffset / (startOffset - endOffset));  time = a + (b - a) * progress;  smoothed: p += (target - p)(1 - e^(-dt/scrub))
```

The smoothing is exponential rather than `p += (target-p)*k` because the naive form is FRAMERATE-DEPENDENT — it converges twice as fast at 120fps as at 60, so the same scene feels different per machine and matches neither at export.

**`TimelinePosition`**

```
start = base + offset;  base = timelineEnd | prevStart ("<") | prevEnd (">") | labels[name];  offset = n seconds, or n% of insertDuration after +=/-=, or n% of prevDuration after a bare < or >
```

The percentage basis DIFFERS by form: "-=25%" is a quarter of the clip being inserted, "<25%" is a quarter of the previous clip. They agree only when the two clips are the same length.

**`Stagger`**

```
delay_i = ease(d_i / max(d)) * total;  total = amount, or each * max(d);  d_i = distance from the origin in index steps (or grid cells)
```

Distances are ranks, not seconds — scaling happens once, so `each` and `amount` cannot drift apart. Delays land on `data.animationDelay`, the channel the engine and the SMIL exporter already read.

**`PathSegment`**

```
segment = (P, handleIn, handleOut);  the span P_i -> P_i+1 is the cubic Bezier with controls P_i, P_i + handleOut_i, P_i+1 + handleIn_i+1, P_i+1
```

Handles are stored RELATIVE to their own anchor, so moving an anchor carries both handles with it and the curve keeps its shape. Absolute control points are the commoner convention and the one that makes a move look like a deformation.

**`BezierHandle`**

```
handleIn, handleOut in R^2, relative to P;  |H| = 0 makes the adjoining span a straight line;  handleOut = -handleIn is a symmetric (mirrored) join
```

**`PoseSequence`**

```
theta_b(t) = lerpShortest(theta_b[i], theta_b[i+1], ease(u)),  u = (t - t_i) / (t_{i+1} - t_i);  looping: t <- t mod P
```

Sampled as a pure function of playbackTime, which is what makes it scrub and bake rather than drift.

**`MotionClip`**

```
t' = (t - t_0) * D / (t_last - t_0)
```

Authored times are rebased to zero and scaled to the requested duration, so every clip speaks absolute seconds before any joining happens.

**`MotionSeam`**

```
w = smoothstep(f) = f^2 (3 - 2f),  f = (t - t_seam) / blend;  theta_b = lerpShortest(A_b(t), B_b(t - t_seam + phi), w);  residual = mean_b |delta(A_b, B_b)|
```

A linear cross-fade has a visible corner at both ends. The residual is reported in degrees because it is the honest measure of how good the join can be: near zero is a match, large means the blend is hiding a cut.

**`PoseBlend`**

```
delta(a, b) = ((b - a + 180) mod 360) - 180  in (-180, 180];  v = a + delta * t
```

The wrap is the whole point: without it, 170 deg to -170 deg travels 340 deg the wrong way and a limb rotates backwards.

**`PoseLayer`**

```
theta_b += A_layer * cycle(frac(t / P_layer))
```

Additive over whatever pose is current, on its own period, which is what lets a breath run underneath a walk.

**`GaitCycle`**

```
phi* = argmin_phi (1/|B|) sum_b |delta(A_b, B_b(phi))|,  phi sampled at N = 64 points of the cycle
```

Entering a cycle at the phase nearest the outgoing pose. Measured on a walk entered mid-stride: peak joint speed through the seam 1.00x the clip body, against 1.40x unmatched.

**`LocomotionTrack`**

```
local = t_0 + (t_scene - start) * speed;  looped: t_0 + ((local - t_0) mod P + P) mod P;  p = ease-lerp between the bracketing keys
```

local is in SCENE SECONDS, not a 0..1 fraction — a track shorter than the performance lands the figure early and leaves it standing.

**`SecondaryMotion`**

```
v = x - x_prev;  F = k (x_target - x) - c v / dt + g;  x' = x + v + (F/m) dt^2;  then Jakobsen length constraints
```

Position Verlet: velocity is implied by the previous position rather than stored, so the constraint pass can move a particle without corrupting its momentum.

**`BakedAnimation`**

```
N = ceil(D * fps),  dt = 1 / fps;  sample every attached item at t_k = k dt, then RDP-simplify in value space
```

Simplification is in VALUE space, not time: a held pose costs two keys however long it is held.

**`MotionCapture`**

```
theta_bone = atan2(p_to - p_from), One Euro filtered;  theta <- (1 - w) theta_prev + w theta_new,  w scaled by landmark confidence
```

Landmarks are WORLD space and bone.angle is LOCAL, so the parent chain has to be subtracted before the angle means anything.

**`motionWalk`**

```
u = frac(t / P);  pose = sequence[floor(u n)] blended to its successor
```

**`motionBreath`**

```
theta_spine = theta_rest +/- A sin(2 pi t / P)
```

**`motionJump`**

```
y(t) = y_0 + v_0 t - (1/2) g t^2, with a squash scale applied on landing
```

**`stitchSatin`**

```
stitch_i spans A(t_i) -> B(t_i),  t_i = i / (n - 1);  n = ceil(arcLength(A) / rowGap)
```

Counted from the EDGE arc length, not the bounding box: a curved side is longer than the box it sits in, and sizing to the box leaves visible banding.

**`stitchLongAndShort`**

```
len_i = clamp(L (1 + U(-1, 1) variance), 1, maxLen);  row offset = (row mod 2) * stagger * L
```

The length variance IS the shading — it is what makes successive rows interlock instead of banding.

**`stitchSeed`**

```
centre ~ rejection-sampled uniform over the polygon;  angle ~ U(0, 2 pi);  endpoints = centre -/+ (L/2)(cos a, sin a)
```

**`stitchStem`**

```
advance = L (1 - overlap);  stitch_k from arc d_k = k * advance to d_k + L, rotated by the slant about its midpoint
```

Walked by ARC LENGTH: stepping per polyline segment bunches the stitches wherever the source curve happened to be finely sampled.

**`staggerFromStart`**

```
d_i = i,  where i is the item's 0-based index and d is its distance rank
```

**`staggerFromEnd`**

```
d_i = (n - 1) - i,  where n is the item count and i the 0-based index
```

**`staggerFromCenter`**

```
d_i = |i - (n-1)/2|;  grid: hypot(|c - c0|, |r - r0|)
```

**`staggerFromEdges`**

```
d_i = min(i, n-1-i);  grid: min(r, rows-1-r, c, cols-1-c)
```

**`staggerFromRandom`**

```
d = a seeded permutation of 0..n-1
```

**`flowFieldHand`**

```
angle(c, r) = 0.2 (0.5 ba sin(bs r c + phi)) cos(t) + noise(c, r) ba 0.7,  ba ~ U{5..10}, bs ~ U(0.2, 0.8), phi ~ U{15..25}
```

**`flowFieldCurved`**

```
angle(c, r) = 3 map(noise(0.02 c + 0.03 t, 0.02 r + 0.03 t), 0, 1, -ar, ar),  ar ~ U{-10..10}
```

**`flowFieldZigzag`**

```
angle <- angle + dif;  dif <- -dif  per cell, and again at each column end;  dif_0 = ar ~ U{-30..-15} + |44 sin(t)|
```

**`flowFieldWaves`**

```
angle(c, r) = ba sin(sr c) cos(cr r) + U{-3..3},  sr ~ U{10..15} + 5 sin(t), cr ~ U{3..6} + 3 cos(t), ba ~ U{20..35}
```

**`flowFieldSeabed`**

```
angle(c, r) = 1.1 ba sin(bs r c + phi) cos(t),  bs ~ U(0.4, 0.8), ba ~ U{18..26}, phi ~ U{15..20}
```

**`flowFieldSpiral`**

```
angle(c, r) = atan2( sum_k w_k sin(th_k), sum_k w_k cos(th_k) ),  w_k = 1 / (d_k^2 + 1),  th_k = dir (atan2(dy, dx) + offset), offset ~ U{65..80} deg
```

**`flowFieldColumns`**

```
angle(c) = amp sin(freq c),  freq ~ U{3..8}, amp ~ U{25..45}
```

**`editMoveAnchor`**

```
P' = P + d;  handleIn and handleOut unchanged (they are relative)
```

**`editMoveHandle`**

```
H' = H + d,  H being relative to its own anchor, which does not move
```

**`editRotateHandles`**

```
H' = R(theta) H for each handle;  |H'| = |H|
```

**`editScaleHandle`**

```
H' = s H,  s > 0;  arg(H) is preserved, so only the tension changes
```

**`editMirrorHandles`**

```
handleOut' = -handleIn  (collinear AND equal length)
```

**`editAlignHandles`**

```
handleOut' = -|handleOut| * handleIn / |handleIn|
```

**`editBreakHandles`**

```
no constraint imposed; handleIn and handleOut become independent
```

**`editRetractHandle`**

```
H' = (0, 0);  the adjoining span degenerates to a straight segment
```

**`editCopyHandles`**

```
(handleIn, handleOut)_target <- (handleIn, handleOut)_source
```

**`editInsertSegment`**

```
de Casteljau split at t: the two resulting spans trace the original curve exactly
```

**`editRemoveSegment`**

```
the span P_i-1 -> P_i+1 is refitted from the surviving handles; not an inverse of insert
```

**`editReplaceGeometry`**

```
segments <- new list;  anchors and both handles replaced wholesale
```

**`editSmoothPath`**

```
handles solved for continuity through fixed anchors (Catmull-Rom / continuous fitting)
```

**`editSimplifyPath`**

```
least-squares Bezier fitting subject to max deviation <= tolerance
```


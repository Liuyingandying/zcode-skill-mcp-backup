# PinePaper Console / Paper.js API Cheat Sheet

Use this when generating JavaScript for the user to paste into the Code Console at
https://pinepaper.studio/editor, or when you want raw control beyond the MCP tools. The whole API is
global: `const app = window.PinePaper;` and `paper.*` is also available. Agent Mode adds
`window.PinePaperAgent` for batch/smart-export helpers.

## Table of contents
- Create items
- Modify, select, query
- Animate (loops + keyframes)
- Relations
- Generators (backgrounds)
- Effects & filters
- SVG import & images
- Direct Paper.js (boolean ops, custom paths, groups, symbols)
- Scenes
- Export

## Create items — `app.create(type, params)`

> The method is `create` and the first argument is the type string (there's no `createItem`).

Types: `text`, `circle`, `star`, `rectangle`, `triangle`, `polygon`, `ellipse`, `path`, `line`, `arc`.

```javascript
app.create('text',      { content: 'Hello', x: 400, y: 300, fontSize: 48, color: '#4f46e5', fontFamily: 'Arial, sans-serif' });
app.create('circle',    { x: 200, y: 200, radius: 50, color: '#ef4444' });
app.create('star',      { x: 300, y: 300, radius1: 60, radius2: 30, color: '#fbbf24' });
app.create('rectangle', { x: 400, y: 400, width: 100, height: 60, color: '#22c55e' });
app.create('triangle',  { x: 300, y: 200, radius: 50, color: '#f59e0b' });
app.create('polygon',   { x: 500, y: 200, sides: 6, radius: 40, color: '#8b5cf6' }); // hexagon
app.create('ellipse',   { x: 400, y: 300, width: 120, height: 60, color: '#06b6d4' });
```

**Paths** — two ways to define geometry:
```javascript
// From points
app.create('path', { segments: [[100,100],[150,50],[200,100],[250,150]], strokeColor:'#3b82f6', strokeWidth:3, closed:true, smooth:true });
// From SVG path data (best for curves: M L H V C Q A Z)
app.create('path', { pathData: 'M 100 100 L 200 100 L 200 200 Z', fillColor:'#22c55e', strokeColor:'#15803d', strokeWidth:2 });
```
Path params: `segments`, `pathData`, `strokeColor`, `fillColor`, `strokeWidth`, `strokeCap`
(`round|square|butt`), `strokeJoin` (`round|miter|bevel`), `dashArray` (`[dash, gap]`), `closed`,
`smooth`, `simplify`. `line` takes `from`/`to`; `arc` takes `from`/`through`/`to`.

`app.addText('content')` quickly adds centered text.

## Modify, select, query
```javascript
app.modify(item, { x:400, y:300, width:200, height:150, rotation:45, opacity:0.8,
                   color:'#ff0000', strokeColor:'#000', strokeWidth:2,
                   fontSize:48, content:'New', animationType:'pulse', animationSpeed:1.5 });
```
Prefer absolute `width`/`height` over `scale` (scale compounds). Selection: `app.select(query, replace)`
where query is an item, `'item_123'`, `'name:Foo'`, `'all'`, or `{ type:'text' }`. Also:
`app.clearSelection()`, `app.selectedItems`, `app.getItemById(id)`, `app.getItemsByName(name)`,
`app.getAllItems()`, `app.queryItems(match)`, `app.queryItem(match)`, `app.hitTest([x,y])`,
`app.deleteSelected()`, `item.remove()`. Z-order: `bringToFront()`, `sendToBack()`, `moveUp()`,
`moveDown()`. Canvas: `setBackgroundColor()`, `setCanvasSize(w,h,preset)`, `clearCanvas()`.
History: `app.historyManager.saveState()` after batch ops; `.undo()` / `.redo()`.

## Animate
```javascript
// Loop animation. Reliable types: pulse, rotate, bounce, fade, wobble, slide, typewriter.
app.animate(item, { animationType: 'pulse', animationSpeed: 1.0 });

// Keyframe timeline
app.modify(item, { animationType:'keyframe', keyframes: [
  { time:0, properties:{ position:[100,100], opacity:0 }, easing:'easeIn' },
  { time:1, properties:{ position:[400,300], opacity:1 }, easing:'easeOut' }
]});
app.playKeyframeTimeline(2, true); // duration seconds, loop
```

## Relations (declarative behavior between items)
```javascript
const sunId = sun.data.registryId, earthId = earth.data.registryId;
app.addRelation(earthId, sunId, 'orbits', { radius:200, speed:0.1 });
app.addRelation(labelId, earthId, 'attached_to', { offset:[0,-30] });
```

## Generators (procedural backgrounds) — async
```javascript
await app.executeGenerator('drawSunburst',    { colors:['#6366f1','#8b5cf6','#a855f7'], rayCount:16, bgColor:'#1e1b4b' });
await app.executeGenerator('drawSunsetScene', { skyColors:['#1e3a5f','#fb923c','#fbbf24'], cloudCount:5 });
await app.executeGenerator('drawGrid',        { gridType:'dots', spacing:30, lineColor:'#334155', bgColor:'#0f172a' });
```

## Effects & filters
```javascript
app.applyEffect(item, 'sparkle', { color:'#fbbf24', speed:1.0, size:3 });
app.applyEffect(item, 'blast',   { color:'#ef4444', radius:100, count:20 });
app.filterSystem.addFilter('grayscale', { intensity:0.5 });
app.filterSystem.addFilter('vignette',  { intensity:0.3, radius:0.5 });
app.filterSystem.applyPreset('cinematic');
```

## SVG import & images
```javascript
const svg = app.importSVG('<svg viewBox="0 0 100 100"><circle cx="50" cy="50" r="40" fill="#3b82f6"/></svg>');
svg.position = app.view.center; svg.scale(2);
app.animate(svg, { animationType:'rotate', animationSpeed:0.3 });

const entry  = await app.imageTools.uploadFromURL('https://example.com/logo.png');
const raster = await app.imageTools.placeImage(entry.id, { position:[400,300], maxWidth:300, maxHeight:200 });
app.imageTools.applyMask(raster, 'circle'); // circle | rounded | hexagon | star
```

## Direct Paper.js (advanced)
```javascript
// Boolean operation -> register so it's interactive
const c = new paper.Path.Circle({ center:[200,200], radius:80 });
const r = new paper.Path.Rectangle({ point:[150,150], size:[100,100] });
const cut = c.subtract(r); cut.fillColor = '#8b5cf6';
app.registerItem(cut, 'compound'); c.remove(); r.remove();

// Group as one unit (e.g. a badge)
const g = new paper.Group();
g.addChildren([ /* paths, PointText, ... */ ]);
app.registerItem(g, 'badge', { text:'NEW' });

// Symbols for many repeats (memory efficient)
const sym = app.createSymbol(app.create('star',{x:0,y:0,radius1:20,radius2:10,color:'#fbbf24'}));
app.placeSymbol(sym, [200,200]);
```
Register any raw Paper.js item with `app.registerItem(item, type, props)` so it becomes selectable,
draggable, and exportable. Prefer `app.create()` for simple shapes.

## Character/illustration tip
Compose from multiple `path` items (head, ears, eyes, body as separate paths) so each part can
animate independently. Use Bézier (`C`,`Q`) in `pathData` for organic curves; `smooth:true` with
`segments` for blobby shapes.

## Scenes
```javascript
app.sceneManager.saveCurrentAsScene('Scene 1');
app.sceneManager.createScene('Scene 2');
app.sceneManager.createChain([s1, s2, s3], { autoPlay:true, duration:3000 });
```

## Export
```javascript
const animatedSvg = app.exportAnimatedSVG(); // animated SVG (SMIL)
app.startRecording(); /* let it play */ app.stopRecording(); // WebM, downloads
const projectJson = app.exportProjectJSON();  // full backup
const template    = app.exportTemplate();     // portable/shareable
```
For MP4/GIF/PDF/PNG/Lottie/HTML-widget exports, use the editor's Export panel (or the MCP
`pinepaper_agent_export` tool on the MCP path).

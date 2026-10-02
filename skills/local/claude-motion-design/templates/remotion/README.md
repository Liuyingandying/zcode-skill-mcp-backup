# templates/remotion — 可实例化工程

Claude 逆向语法锁在 `src/` 里；你只写 `content/scenes.json`。

## 实例化（30 秒）

```bash
cp -r . /path/to/my-film && cd /path/to/my-film
npm install                      # 本机：npm_config_cache 指向非 C 盘
# 编辑 content/scenes.json（字段说明见同目录 scenes.example.json 顶部 _readme）
# 照片放 public/photos/
npm run build && npm run render  # → out/film.mp4
```

## 目录

```
content/scenes.json        ← 唯一内容文件（文案/图片/时间线）
public/photos/             ← 照片素材
src/engine/ScenePlayer.tsx # 场景引擎：四型场景 + 硬切编排 + BGM 音量自动化
src/scenes/scenes.tsx      # PhotoScene(2.5D视差) YearCardScene BrandEndcard TextureScene
src/scenes/overlays.tsx    # SerifLine(蒙太奇弹入) FilmGrain Vignette KenBurns
src/components/
  Camera.tsx               # 缓推 rig（4 easing）
  TextReveal.tsx           # spring 逐词 reveal + Kicker（收束/现代感段落用）
  SceneTransition.tsx      # Crossfade / FadeToBlack（硬切为默认，无需组件）
  Background.tsx           # AmbientBackdrop（底色+辉光+颗粒+暗角）
  Texture.tsx              # 纹理注册表 re-export
src/textures/              # 12 种程序化纹理（种子化 feTurbulence，零版权）
src/styles/theme.ts        # 色彩/字体/字号/运动 tokens —— 改品牌色只动这里
```

## 场景四型速查

```jsonc
{ "kind": "texture",  "texture": "dawn-limb", "start": 0, "end": 40,
  "camera": {"amount": 0.05}, "text": {"lines": ["一句"], "enterAt": 20} }
{ "kind": "photo",    "photo": "p.jpg", "archival": true, "start": 40, "end": 130,
  "camera": {"amount": 0.05, "driftX": 6}, "year": "1895",
  "title": "标题", "caption": "说明", "text": {"lines": ["标语行"]} }
{ "kind": "yearCard", "texture": "amber-crust", "start": 130, "end": 200,
  "year": "1895", "title": "名称", "text": {"lines": ["标语"], "enterAt": 160} }
{ "kind": "endcard",  "start": 200, "end": 300 }
```

## 修改视觉 = 改 theme.ts / 组件参数

规则文档在 `../../references/`。改之前先读——**模板内的参数是逆向实测值**，
降档（如文字弹入 >6f、镜头推近 >6%）会破坏风格保真。

## 纹理 id 一览

`dawn-limb`（黎明晨昏线，开场/收束）`amber-crust`（琥珀地壳）`amber-planet`
`teal-planet` `red-planet` `ink-planet`（黑白墨）`batik`（织染）`gold-dust`（鎏金）
`ember-field`（余烬）`blueprint`（蓝图线弧）`cream-leaf`（纸+叶）`paper-print`（版画）

---
name: claude-motion-design
description: Claude Opus 5.5 官方宣传片逆向成果的固化引擎——用已有 motion grammar（衬线字锚定/硬切蒙太奇/camera 缓推/年卡/档案照视差/收束卡）生成发布会级品牌视频。当任务要求制作产品发布片、科技宣传片、AI 项目介绍、高端品牌视频、高校/机构历史品牌片，或用户点名 "Claude 风格/发布会级/不要 PPT 感" 时使用。输入项目资料+时长+品牌信息，输出 content JSON → 渲染成片；不要重新逆向 Claude，不要重新设计视觉系统。
---

# claude-motion-design：Claude 风格 Motion Design 生成引擎

一次 Claude Opus 5.5 官方宣传片逆向（2026-10，`claude-opus55-video-lab/reference/analysis/SHOT_ANALYSIS.md`）的固化成果。本 Skill 把逆向出的 motion grammar 变成**可直接实例化的 Remotion 模板**：新视频任务只需提供内容 JSON，视觉系统锁定在模板组件内。

## 什么时候使用（以及不使用）

✅ 使用：产品发布片 / 科技宣传片 / AI 项目介绍 / 高端品牌视频 / 机构历史品牌片 / 任何"要发布会质感"的短视频（15–120s）。
❌ 不使用：教学讲解、Vlog、信息密度高的说明视频、需要大量动态图表的数据视频。

## 硬性设计原则（违反任何一条 = 不许出片）

1. **镜头先于文字**——开场至少 1 个无文字长镜（≥1.2s）确立世界，文字后到。
2. **每 3–5 秒产生视觉变化**——剪切、文字落点、或机位推进，任选其一。
3. **保持高级留白**——同屏至多 1 个信息主体（一个大字/一张照片），禁止堆叠。
4. **避免模板化转场**——蒙太奇段落 100% 硬切；只允许两种"软"时刻：场景交叉淡化（≤18f）与结尾淡黑。
5. **使用 camera movement**——每个镜头必须有 `interpolate` 缓推（1.00→1.03~1.06），禁止任何镜头完全静止（收束卡辉光呼吸除外）。
6. **动画只用 spring/interpolate/easing**——禁 CSS transition、禁 `Math.random`/`Date.now`（一切伪随机走 mulberry32 种子）。
7. **文字层绝对静止**——生命感全部来自背景层（照片缓推/纹理漂移/颗粒沸动）。

## 视觉系统速查（详见 references/）

- 深空底 `#0A0E12`/`#0B111A` + 象牙字 `#F0EEE4` + 琥珀母题 `#C8722E`（彩板见 color_system.md）
- 衬线字体（中文 Noto Serif SC / 西文 Source Serif 4），字距 0.1–0.3em
- 文字锚定画面 30–47% 带区（年 34% / 题 45.5% / 注 54% / 标语 30%）
- 蒙太奇节奏：开场 2 长镜（1.2s+1.5s）→ 加速剪切（0.4–0.8s）→ 文字段 5–8s/镜 → 收束卡 3.5–4.5s
- 100% 硬切；结尾"先抑后扬"：产品卡静场 → 品牌字 + 黎明/辉光升起

## 使用流程（模板入口）

```bash
# 1. 实例化（复制模板，勿改模板本体）
cp -r templates/remotion my-new-film && cd my-new-film
npm install   # remotion 4.0.484 + react 18，本机记得 npm_config_cache 指向非 C 盘

# 2. 唯一需要写的文件：content/scenes.json
#    字段说明见 content/scenes.example.json 顶部注释
# 3. 照片放 public/photos/（历史照片建议 archival: true）

# 4. 预览与渲染
npx remotion studio --no-open
npm run render        # → out/film.mp4（已固化 --concurrency=1）
```

`scenes.json` 场景四型（引擎已实现，勿自造）：
`texture`（纹理+衬线行）/ `photo`（档案照 2.5D 视差+题注）/ `yearCard`（大年份+名）/ `endcard`（品牌收束卡+辉光）/ `mapPath`（极简地图路径，route.points+labels）；photo 型支持 `photoCrop`（归一化裁切窗，特写起手——见 visual_metaphor.md）。

## 质量门（渲染完不算完成）

1. `npm run build`（tsc 严格）零错误；
2. 渲染后 ffmpeg 抽 ≥5 帧（输出侧 seek）逐帧目检：文字无重叠、层级清晰、无 PPT 感；
3. 对照 references/shot_grammar.md 检查节奏：开场有无长镜？3–5s 有无变化？收束是否先抑后扬？
4. 首帧/尾帧对照 Claude 参考：`claude-opus55-video-lab/reference/analysis/contact-sheet-ref.jpg`。

## 文件地图

| 路径 | 内容 |
|---|---|
| `references/visual_language.md` | 总视觉语言（动静分层/留白/色彩叙事） |
| `references/shot_grammar.md` | 镜头语法：五幕结构、剪切节奏、场景四型 |
| `references/typography.md` | 字体/字号比例/层级/字距规则 |
| `references/camera_rules.md` | 相机规则：缓推参数、easing 族、禁项 |
| `references/transition_rules.md` | 转场规则：硬切为纲、两种合法软化 |
| `references/color_system.md` | 色彩系统 tokens 与用法 |
| `templates/remotion/` | 可实例化 Remotion 工程（组件锁死视觉系统） |
| `examples/` | 实例索引（首个：TJU 20s 验证片） |

## 已知边界

- 参考片为无 UI 的情绪品牌片；如需 UI 窗口/终端演示，改用 ccvideo（MIT，见 claude-opus55-video-lab/_vendor/）；
- 音频：模板不含 BGM（按需用 Mixkit 免费曲库 + 音量自动化，模式见 claude-opus55-video-lab/tju-history/src/TJUHistory.tsx 历史）；
- 中文衬线经 @remotion/google-fonts/NotoSerifSC 按需分块加载，首渲需网络。

## 动画层依赖（V1 起）

模板的动画组件（Camera/TextReveal/Background/FilmGrain/Vignette/Transitions + tokens）
已抽取为本地包 **`claude-motion-core`**（工作区根），模板经 `file:` 依赖引用——
**唯一源码，禁止复制组件进任何工程**。实例化后改动画 = 改 core 源码 + 在消费者
`npm install` 刷新。配置要点（否则 hooks 崩溃）：core 不自带 react/remotion
node_modules；消费者 remotion.config 用 `process.cwd()`（__dirname 指向 CLI dist）
把 `resolve.modules` 回退指向宿主 node_modules。详见 CLAUDE_MOTION_SKILL_V1_REPORT.md 第四节。

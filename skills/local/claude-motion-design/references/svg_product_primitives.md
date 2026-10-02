# svg_product_primitives.md — SVG 产品场景原语速查

> 实现位置：实例 `src/scenes/SvgScenes.tsx`（经 `SvgSceneHost` 注册表消费）。
> 所有原语确定性（mulberry32 / interpolate / spring），禁 SMIL / Math.random。

## 1. FragmentCard（碎片卡片，P 幕）

互不相连的信息碎片：`{title, kind}`；低饱和描边、随机微颤
（`Math.sin(frame/30 + seed)*2px`）、无常亮状态灯。 flock 布局 3×2 或环形。
**关键**：卡片间无连线（连接感是 C 幕才给的）。

## 2. WanderLight（穿越光点，C 幕）

单光源沿贝塞尔/样条巡航（pointAt + progress），尾部 4–6 个衰减光斑
（`opacity = 0.9 - t*k`）。品牌色第一次出现。触达卡片 → 卡片描边转品牌色 + LED 亮。

## 3. MemoryCluster（记忆缸体+节点网络，M 幕）

复用 v1 45s 的 Memory 缸体；外围 8–12 节点小网络（mulberry32 环形），
涓流包沿弧线读写（双向，相位错开）。文字"它记得你"作为 narration 而非器件标签。

## 4. SkillChip / McpBus / ExecRing（A 幕）

复用 v1 45s：芯片网格（spring 飞入 + stagger + LED 转 amber + 总线虚线）、
MCP 竖总线（draw-on + 包）、执行状态机（进度环 fill → 对勾 draw-on → 他片变暗）。
产品化差异：芯片文案改收益动词（ARRANGE / REMEMBER / LEARN…）。

## 5. Avatar（Companion）

Firefly 桌宠 SVG（触角辉光双灯/头部环/眨眼窗口/发光腹部/微笑态）。
扩展位：`mood: normal|happy|thinking`；对话气泡 `Bubble(x,y,w,text,side,s)`
spring 滑入 + 打字三点。Avatar 出场 = 节点汇聚（spring gather）。

## 6. BrandConvergence（品牌汇聚，B 幕）

全部活跃节点 spring 汇聚至中心辉光球（呼吸）→ 触角标记 → 衬线字标 →
tagline → 淡黑。参数：`gatherSprings` / `nameAt` / `taglineAt`。

## 尺寸/色彩约定

- 画布 1920×1080；核心半径 64–72；芯片 330×72（网格 420 间距）；
- 品牌色 amberBright `#E8A25C` / amber `#C8722E`；P 幕禁品牌色（冷灰 `#3A4652`）；
- 文字：mono（器件标签 22–26px·ls3）+ serifCjk（narration/tagline）；
- 颗粒 FilmGrain + Vignette 全程；包运动速率 42–50 帧/程。

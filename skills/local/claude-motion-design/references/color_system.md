# color_system.md — 色彩系统

全部 token 定义在 `templates/remotion/src/styles/theme.ts`，组件只 import 不硬编码。

## 核心 tokens

| token | 值 | 角色 |
|---|---|---|
| `ivory` | `#F0EEE4` | 一切文字（单色字系统） |
| `deepSpace` | `#0A0E12` | 开场/通用底 |
| `endcardNavy` | `#0B111A` | 收束卡底 |
| `glowCyan` | `#4E8EA8` | 收束卡底部辉光（冷） |
| `amber` | `#C8722E` | 暖琥珀母题（纹理/黎明/粒子） |
| `amberBright` / `amberPale` | `#E8A25C` / `#F2C98A` | 琥珀高光两档 |
| `emberRed` | `#D9552B` | 黎明轮缘红 |
| `teal` / `slate` | `#0E6E7E` / `#1E3A5C` | 冷对拍（每片至多一拍） |
| `cream` / `gold` | `#EAE4D5` / `#B8862A` | 亮对拍（纸张/鎏金） |
| `sealRed` | `#9E2B25` | 印章红——唯一的中式点睛，只许点缀 |

## 用法规则

1. **暗部为纲**：任何一帧的 60%+ 面积应为深色（#0A–#24 区间）；亮镜头（cream 系）
   是对比拍，每片 ≤2 拍、每拍 ≤1.5s；
2. **品牌主色映射**：把品牌主色替换 `amber`/`amberBright`/`emberRed` 三档（保持深→亮），
   `glowCyan` 换品牌辅色；**不要**动 ivory 和深空底——那是语法的一部分；
3. **辉光公式**：收束卡底部辉光 = 径向渐变（120%×62% @ 50%,118%）双层
   （辅色 0.5 → 主色 0.32 → 透明），叠加 `Math.sin(frame/52)` 呼吸 ±0.06；
4. **渐变 vs 平色**：禁止任何大面积平色块——底色上必须有噪声（grain ≥0.05）或
   辉光渐变，否则立刻 PPT 化；
5. **对比拍旋转**：多镜头蒙太奇中冷/亮对拍轮换出现（teal → blueprint → cream），
   节奏与剪切加速对齐。

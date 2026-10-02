# camera_rules.md — 相机规则

## 总纲（参考片铁律）

**没有静止的镜头，也没有持续的 zoom。** 唯一合法运动是"镜头级缓推"：
每镜头 scale 从 1.00（或 1.02 起手）线性推进 3–6%，配合 ≤10px 横向漂移。
禁止持续变焦、禁止平摇甩镜、禁止任何镜头完全静止（收束卡辉光呼吸除外）。

## 参数（Camera.tsx）

| 场景型 | amount | driftX | ease |
|---|---|---|---|
| 开场长镜 | 0.05–0.055 | 0 | easeInOut |
| 铺垫长镜 | 0.04–0.045 | ±8 | easeInOut |
| 短切蒙太奇 | 0（省略） | 0 | — |
| 照片段 | 0.045–0.06 | ±6–10 | easeInOut |
| yearCard | 0.04 | 0 | easeInOut |
| 收束卡 | 无相机（辉光呼吸 = Math.sin frame/52） | — | — |

## easing 族（Camera.tsx 内置）

- `linear`：纹理内部漂移用；
- `easeInOut`（默认）：镜头推近——三次 smoothstep，起停无感；
- `easeOut`：文字弹入（与 Easing.out(quad) 同族）；
- `springish`：1-(1-t)^4，需要"落定感"的长推。

**禁项**：bounce/elastic（参考片无弹性运动）；任何 >8% 的单镜头缩放（文字会肉眼可见地漂）。

## 2.5D 视差（PhotoScene 内建）

照片场景自动生成双层：
- 远景层：同图 scale 1.12→1.20 + **反向**漂移（driftX × -1.6）+ blur 26px + brightness 0.5；
- 锐利层：KenBurns 正常推近；
两层速度差即深度，无需 three.js、无需深度图，且不改变历史照片内容。

## 纹理内部运动

每个程序化纹理自带 `frameDrift(frame, amp, period)` 正弦漂移（噪声层/轮廓线独立位移）
——镜头不动时画面仍在呼吸。新纹理必须包含至少一层 frameDrift。
